from __future__ import annotations

import csv
import io
import re
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4
from xml.etree import ElementTree

import uvicorn
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator
from starlette.routing import Router as StarletteRouter

from app.core.entities import Channel as PreferenceChannel
from app.core.models import Channel
from app.modules.analytics.service import AnalyticsRepository, AnalyticsService
from app.modules.audit.service import AuditLogRepository, AuditService
from app.modules.integration.auth import AuthService
from app.modules.integration.persistence import JsonFileStore, TripRepository
from app.modules.notification.concierge_playbook import MESSAGE_TEMPLATES
from app.modules.notification.models import NotificationTask
from app.modules.notification.rule_service import NotificationRuleRepository, RuleValidationError
from app.modules.notification.service import NotificationAttemptRepository, NotificationService
from app.services.preference_service import UserPreferenceService
from app.services.template_service import TemplateService

UTC = UTC


def _patch_starlette_router_compat() -> None:
    """
    Compatibility shim for environments where FastAPI and Starlette versions
    are temporarily misaligned (FastAPI passes on_startup/on_shutdown).
    """

    if getattr(StarletteRouter.__init__, "_fastapi_compat_patched", False):
        return

    original_init = StarletteRouter.__init__

    def _patched_init(self: StarletteRouter, *args: Any, **kwargs: Any) -> None:
        kwargs.pop("on_startup", None)
        kwargs.pop("on_shutdown", None)
        original_init(self, *args, **kwargs)

    _patched_init._fastapi_compat_patched = True  # type: ignore[attr-defined]
    StarletteRouter.__init__ = _patched_init  # type: ignore[assignment]


@dataclass(slots=True)
class Response:
    status: int
    body: dict[str, Any]


@dataclass(slots=True)
class AppContext:
    store: JsonFileStore
    auth_service: AuthService
    trip_repository: TripRepository
    template_service: TemplateService
    preference_service: UserPreferenceService
    notification_attempt_repository: NotificationAttemptRepository
    notification_rule_repository: NotificationRuleRepository
    notification_service: NotificationService
    audit_service: AuditService
    analytics_service: AnalyticsService


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class PreferenceUpdateRequest(BaseModel):
    channels: list[str] = Field(default_factory=list)
    quiet_hours: list[int] | dict[str, Any] = Field(default_factory=lambda: [23, 7])
    max_notifications_per_hour: int | None = None
    auto_escalation: bool | None = None
    aggregate_notifications: bool | None = None
    allow_marketing: bool | None = None


class TemplateCreateRequest(BaseModel):
    name: str
    content: str
    channel: str = "sms"
    notification_type: str = "daily_reminder"
    is_active: bool = True


class TemplateUpdateRequest(BaseModel):
    name: str | None = None
    content: str | None = None
    channel: str | None = None
    notification_type: str | None = None
    is_active: bool | None = None


class NotificationRuleCreateRequest(BaseModel):
    name: str
    stage: str
    time_slot: str
    scene: str
    channels: list[str] | None = None
    template_id: str | None = None
    enabled: bool = True
    priority: int = 100
    conditions: dict[str, Any] | None = None


class NotificationRuleUpdateRequest(BaseModel):
    name: str | None = None
    stage: str | None = None
    time_slot: str | None = None
    scene: str | None = None
    channels: list[str] | None = None
    template_id: str | None = None
    enabled: bool | None = None
    priority: int | None = None
    conditions: dict[str, Any] | None = None


class TripCreateRequest(BaseModel):
    destination: str
    team: str | None = None
    team_id: str | None = None
    start_date: str
    end_date: str
    participants: int = 0
    status: str = "计划中"


class TripUpdateRequest(BaseModel):
    destination: str | None = None
    team: str | None = None
    team_id: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    participants: int | None = None
    status: str | None = None

    @field_validator("team", "team_id")
    @classmethod
    def validate_team_fields(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return value.strip()


class NotificationSendRequest(BaseModel):
    template_id: str | None = None
    trip_id: str | None = None
    trip: str | None = None
    team: str | None = None
    team_id: str | None = None
    customer_name: str | None = None
    destination: str | None = None
    channel: str = "sms"


def _ok(data: Any) -> dict[str, Any]:
    return {"code": 200, "data": data}


def _error(status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"code": status, "error": message})


def _ok_with_message(data: Any, message: str) -> dict[str, Any]:
    return {"code": 200, "message": message, "data": data}


def _parse_channel(value: str) -> Channel:
    raw = value.strip().lower()
    if raw in {"短信"}:
        raw = "sms"
    if raw in {"企业微信", "wechat", "wechat_work"}:
        raw = "wechat_work_group"
    matched = next((item for item in Channel if item.value == raw), None)
    return matched or Channel.SMS


def _normalize_trip_status(value: str) -> str:
    mapping = {
        "计划中": "planned",
        "planned": "planned",
        "进行中": "in_progress",
        "active": "in_progress",
        "in_progress": "in_progress",
        "已完成": "completed",
        "completed": "completed",
        "已取消": "cancelled",
        "cancelled": "cancelled",
    }
    return mapping.get(value, value)


def _to_internal_preference_channel(value: str) -> str:
    raw = value.strip().lower()
    mapping = {
        "wechat_work_group": "push",
        "wechat": "push",
        "push": "push",
        "sms": "sms",
        "email": "email",
    }
    return mapping.get(raw, raw)


def _to_api_preference_channel(value: str) -> str:
    raw = value.strip().lower()
    if raw == "push":
        return "wechat_work_group"
    return raw


def _normalize_preference_payload(payload: dict[str, Any]) -> dict[str, Any]:
    channels = payload.get("channels", [])
    normalized_channels: list[str] = []
    if isinstance(channels, list):
        for item in channels:
            normalized = _to_api_preference_channel(str(item))
            if normalized not in {"sms", "wechat_work_group", "email"}:
                continue
            if normalized not in normalized_channels:
                normalized_channels.append(normalized)
    result = dict(payload)
    result["channels"] = normalized_channels
    return result


def _resolve_team_id(team: str | None, team_id: str | None) -> str:
    return (team_id or team or "").strip()


def _normalize_import_header(value: str) -> str:
    return value.strip().lower().replace(" ", "").replace("_", "")


def _read_csv_rows(raw: bytes) -> list[dict[str, str]]:
    decoded = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(decoded))
    return [
        {
            str(key): (str(value).strip() if value is not None else "")
            for key, value in row.items()
            if key is not None
        }
        for row in reader
    ]


def _extract_column_index(ref: str) -> int:
    letters = "".join(char for char in ref if char.isalpha()).upper()
    index = 0
    for letter in letters:
        index = index * 26 + (ord(letter) - ord("A") + 1)
    return max(index - 1, 0)


def _read_xlsx_rows(raw: bytes) -> list[dict[str, str]]:
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        workbook_xml = archive.read("xl/workbook.xml")
        workbook = ElementTree.fromstring(workbook_xml)
        namespaces = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        first_sheet = workbook.find("main:sheets/main:sheet", namespaces)
        if first_sheet is None:
            return []
        relation_id = first_sheet.attrib.get(
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        )
        if relation_id is None:
            return []

        workbook_rels = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_namespaces = {"rel": "http://schemas.openxmlformats.org/package/2006/relationships"}
        rel = workbook_rels.find(f"rel:Relationship[@Id='{relation_id}']", rel_namespaces)
        if rel is None:
            return []
        target = rel.attrib.get("Target", "")
        worksheet_path = f"xl/{target}" if not target.startswith("xl/") else target
        worksheet = ElementTree.fromstring(archive.read(worksheet_path))

        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared_root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in shared_root.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si"):
                text = "".join(
                    node.text or ""
                    for node in item.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")
                )
                shared_strings.append(text)

        parsed_rows: list[list[str]] = []
        for row_node in worksheet.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"):
            cells: dict[int, str] = {}
            for cell in row_node.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"):
                ref = cell.attrib.get("r", "")
                cell_type = cell.attrib.get("t", "")
                index = _extract_column_index(ref)
                if cell_type == "inlineStr":
                    text_node = cell.find(
                        ".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"
                    )
                    cells[index] = (text_node.text or "").strip() if text_node is not None else ""
                    continue
                value_node = cell.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
                value = (value_node.text or "").strip() if value_node is not None else ""
                if cell_type == "s" and value.isdigit():
                    shared_index = int(value)
                    cells[index] = (
                        shared_strings[shared_index]
                        if 0 <= shared_index < len(shared_strings)
                        else ""
                    )
                else:
                    cells[index] = value
            if not cells:
                continue
            width = max(cells) + 1
            parsed_rows.append([cells.get(idx, "").strip() for idx in range(width)])

        if not parsed_rows:
            return []
        headers = [cell for cell in parsed_rows[0]]
        rows: list[dict[str, str]] = []
        for row in parsed_rows[1:]:
            item: dict[str, str] = {}
            for index, header in enumerate(headers):
                if not header:
                    continue
                item[header] = row[index] if index < len(row) else ""
            rows.append(item)
        return rows


def _extract_import_field(row: dict[str, str], aliases: list[str]) -> str:
    normalized_lookup = {_normalize_import_header(key): value for key, value in row.items()}
    for alias in aliases:
        matched = normalized_lookup.get(_normalize_import_header(alias), "")
        if matched:
            return str(matched).strip()
    return ""


def _normalize_excel_serial_date(value: str) -> str:
    if re.fullmatch(r"\d+(\.\d+)?", value):
        serial = float(value)
        base = datetime(1899, 12, 30, tzinfo=UTC)
        return (base + timedelta(days=serial)).date().isoformat()
    normalized = value.replace("/", "-").strip()
    return normalized[:10]


def _serialize_trip(trip: dict[str, Any]) -> dict[str, Any]:
    resolved_team_id = str(trip.get("team_id") or trip.get("team") or "")
    return {
        "id": trip.get("id", ""),
        "destination": trip.get("destination", ""),
        "team_id": resolved_team_id,
        "team": resolved_team_id,
        "start_date": trip.get("start_date", ""),
        "end_date": trip.get("end_date", ""),
        "participants": int(trip.get("participants", 0)),
        "status": _normalize_trip_status(str(trip.get("status", "planned"))),
        "user_id": trip.get("user_id", ""),
        "created_at": trip.get("created_at"),
        "updated_at": trip.get("updated_at"),
    }


def _normalize_history_item(item: dict[str, Any]) -> dict[str, Any]:
    ok = bool(item.get("ok", False))
    raw_status = str(item.get("status", "sent")).lower()
    status = raw_status
    if raw_status in {"", "pending"}:
        status = "sent" if ok else "failed"
    return {
        "id": item.get("attempt_id", ""),
        "attempt_id": item.get("attempt_id", ""),
        "task_id": item.get("task_id", ""),
        "trip_id": item.get("trip_id", ""),
        "team_id": item.get("team_id", ""),
        "team": item.get("team_id", ""),
        "customer_id": item.get("customer_id", ""),
        "attempt_no": int(item.get("attempt_no", 1)),
        "channel": str(item.get("channel", "sms")).lower(),
        "status": status,
        "ok": ok,
        "reason": item.get("reason", ""),
        "provider_message": item.get("provider_message", ""),
        "latency_ms": int(item.get("latency_ms", 0)),
        "attempted_at": item.get("attempted_at"),
    }


def _to_recent_item(item: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_history_item(item)
    return {
        "id": normalized["id"],
        "customer_name": normalized["customer_id"],
        "trip": normalized["trip_id"],
        "team_id": normalized["team_id"],
        "team": normalized["team_id"],
        "channel": normalized["channel"],
        "status": normalized["status"],
        "created_at": normalized["attempted_at"],
    }


def _compute_channel_performance(attempts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, int]] = {}
    for item in attempts:
        channel = str(item.get("channel", "sms")).lower()
        bucket = grouped.setdefault(channel, {"sent": 0, "successful": 0, "failed": 0})
        bucket["sent"] += 1
        if item.get("ok") is True:
            bucket["successful"] += 1
        else:
            bucket["failed"] += 1

    performance: list[dict[str, Any]] = []
    for channel, bucket in grouped.items():
        sent = bucket["sent"]
        success_rate = round((bucket["successful"] / sent) * 100, 1) if sent else 0.0
        performance.append(
            {
                "channel": channel,
                "sent": sent,
                "successful": bucket["successful"],
                "failed": bucket["failed"],
                "rate": f"{success_rate}%",
            }
        )
    return sorted(performance, key=lambda item: int(item["sent"]), reverse=True)


def _compute_top_trips(
    attempts: list[dict[str, Any]],
    trip_repository: TripRepository,
    limit: int = 5,
) -> list[dict[str, Any]]:
    trip_map = {str(trip.get("id")): trip for trip in trip_repository.list()}
    grouped: dict[str, int] = {}
    for item in attempts:
        trip_id = str(item.get("trip_id", "")).strip()
        if not trip_id:
            continue
        grouped[trip_id] = grouped.get(trip_id, 0) + 1

    ranking: list[dict[str, Any]] = []
    for trip_id, notifications in grouped.items():
        trip = trip_map.get(trip_id, {})
        destination = str(trip.get("destination", "")).strip()
        ranking.append(
            {
                "name": destination or trip_id,
                "notifications": notifications,
                "satisfaction": 4.5,
            }
        )

    ranking_sorted = sorted(ranking, key=lambda item: int(item["notifications"]), reverse=True)
    return ranking_sorted[: max(limit, 0)]


def _query_notification_items(
    *,
    repository: NotificationAttemptRepository,
    limit: int,
    trip_id: str | None,
    team_id: str | None,
    customer_id: str | None,
    channel: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    raw_items = repository.list_history(
        limit=None,
        trip_id=trip_id,
        team_id=team_id,
        customer_id=customer_id,
    )
    normalized = [_normalize_history_item(item) for item in raw_items]
    if channel:
        normalized = [item for item in normalized if item["channel"] == channel.lower()]
    if status:
        normalized = [item for item in normalized if item["status"] == status.lower()]
    normalized_sorted = sorted(
        normalized,
        key=lambda item: (str(item.get("attempted_at") or ""), str(item.get("id") or "")),
        reverse=True,
    )
    return normalized_sorted[: max(limit, 0)]


def _serialize_template(template: Any) -> dict[str, Any]:
    status = "enabled" if template.is_active else "disabled"
    return {
        "id": template.id,
        "name": template.name,
        "version": template.version,
        "notification_type": template.notification_type.value,
        "channel": template.channel.value,
        "status": status,
        "enabled": template.is_active,
        "template": template.content,
        "content": template.content,
        "is_active": template.is_active,
        "created_at": template.created_at,
        "updated_at": template.updated_at,
    }


def _seed_default_trips(trip_repository: TripRepository) -> None:
    if trip_repository.list():
        return

    now = datetime.now(tz=UTC).isoformat()
    default_trips: list[dict[str, Any]] = [
        {
            "id": "trip-default-pretrip",
            "destination": "乌鲁木齐-喀纳斯精品线",
            "team": "TEAM-DEMO-PRE",
            "team_id": "TEAM-DEMO-PRE",
            "start_date": "2026-05-08",
            "end_date": "2026-05-14",
            "participants": 18,
            "status": "planned",
            "user_id": "admin",
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "trip-default-ontrip",
            "destination": "伊犁草原深度游",
            "team": "TEAM-DEMO-ON",
            "team_id": "TEAM-DEMO-ON",
            "start_date": "2026-04-20",
            "end_date": "2026-04-26",
            "participants": 22,
            "status": "in_progress",
            "user_id": "admin",
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "trip-default-posttrip",
            "destination": "阿勒泰禾木轻奢团",
            "team": "TEAM-DEMO-POST",
            "team_id": "TEAM-DEMO-POST",
            "start_date": "2026-03-10",
            "end_date": "2026-03-16",
            "participants": 16,
            "status": "completed",
            "user_id": "admin",
            "created_at": now,
            "updated_at": now,
        },
    ]
    for trip in default_trips:
        trip_repository.create(trip)


def _seed_default_notification_rules(
    rule_repository: NotificationRuleRepository, template_id: str
) -> None:
    if rule_repository.list_rules():
        return

    default_rules: list[dict[str, Any]] = [
        {
            "id": "rule-default-pre-3day",
            "name": "行前3天沟通与行程单提醒",
            "stage": "pre_trip",
            "time_slot": "morning",
            "scene": "normal",
            "channels": ["sms", "wechat_work_group"],
            "template_id": template_id,
            "enabled": True,
            "priority": 10,
            "conditions": {"time_node": "出发前3天"},
        },
        {
            "id": "rule-default-pre-1day",
            "name": "行前1天保险核查与群提醒",
            "stage": "pre_trip",
            "time_slot": "evening",
            "scene": "normal",
            "channels": ["wechat_work_group"],
            "template_id": template_id,
            "enabled": True,
            "priority": 20,
            "conditions": {"time_node": "出发前1天"},
        },
        {
            "id": "rule-default-ontrip-daily",
            "name": "行中固定时段温馨提示",
            "stage": "on_trip",
            "time_slot": "all_day",
            "scene": "normal",
            "channels": ["wechat_work_group", "sms"],
            "template_id": template_id,
            "enabled": True,
            "priority": 30,
            "conditions": {"time_node": "每日固定时段"},
        },
        {
            "id": "rule-default-ontrip-scene",
            "name": "行中特殊场景安全提示",
            "stage": "on_trip",
            "time_slot": "afternoon",
            "scene": "weather_alert",
            "channels": ["sms", "wechat_work_group"],
            "template_id": template_id,
            "enabled": True,
            "priority": 40,
            "conditions": {"scene_tags": ["骑马", "高原", "边境口岸", "极寒"]},
        },
        {
            "id": "rule-default-posttrip-survey",
            "name": "下团满意度调研提醒",
            "stage": "post_trip",
            "time_slot": "evening",
            "scene": "normal",
            "channels": ["sms", "email"],
            "template_id": template_id,
            "enabled": True,
            "priority": 50,
            "conditions": {"time_node": "下团即时"},
        },
    ]
    for rule in default_rules:
        rule_repository.create_rule(rule)


def _seed_concierge_templates(template_service: TemplateService) -> None:
    if template_service.list_notification_templates():
        return

    template_specs: list[dict[str, str]] = [
        {
            "name": "行前3天-航班与行前提示",
            "key": "pre_flight_notice",
            "channel": "wechat_work_group",
            "notification_type": "pre_trip_reminder",
        },
        {
            "name": "行前1天-入群欢迎词",
            "key": "group_welcome",
            "channel": "wechat_work_group",
            "notification_type": "pre_trip_reminder",
        },
        {
            "name": "落地首日-乌鲁木齐推荐",
            "key": "urumqi_day1_recommendations",
            "channel": "wechat_work_group",
            "notification_type": "daily_reminder",
        },
        {"name": "晨间提示-春季", "key": "morning_spring", "channel": "sms", "notification_type": "daily_reminder"},
        {"name": "晨间提示-夏季", "key": "morning_summer", "channel": "sms", "notification_type": "daily_reminder"},
        {"name": "晨间提示-秋季", "key": "morning_autumn", "channel": "sms", "notification_type": "daily_reminder"},
        {"name": "晨间提示-冬季", "key": "morning_winter", "channel": "sms", "notification_type": "daily_reminder"},
        {"name": "午间提示-春季", "key": "noon_spring", "channel": "wechat_work_group", "notification_type": "daily_reminder"},
        {"name": "午间提示-夏季", "key": "noon_summer", "channel": "wechat_work_group", "notification_type": "daily_reminder"},
        {"name": "午间提示-秋季", "key": "noon_autumn", "channel": "wechat_work_group", "notification_type": "daily_reminder"},
        {"name": "午间提示-冬季", "key": "noon_winter", "channel": "wechat_work_group", "notification_type": "daily_reminder"},
        {"name": "场景提示-雨天", "key": "noon_rainy", "channel": "wechat_work_group", "notification_type": "risk_alert"},
        {"name": "场景提示-骑马", "key": "horse_riding_notice", "channel": "wechat_work_group", "notification_type": "risk_alert"},
        {"name": "场景提示-滑雪日", "key": "ski_day_notice", "channel": "wechat_work_group", "notification_type": "risk_alert"},
        {
            "name": "晚间播报-次日行程",
            "key": "evening_next_day_preview",
            "channel": "wechat_work_group",
            "notification_type": "daily_reminder",
        },
        {
            "name": "行中协同-问题协调",
            "key": "issue_coordination_notice",
            "channel": "wechat_work_group",
            "notification_type": "complaint_escalation",
        },
        {
            "name": "下团调研-满意度回访",
            "key": "post_trip_survey_notice",
            "channel": "sms",
            "notification_type": "satisfaction",
        },
        {"name": "下团欢送词", "key": "farewell_message", "channel": "wechat_work_group", "notification_type": "farewell"},
        {"name": "解散群文案", "key": "group_close_message", "channel": "wechat_work_group", "notification_type": "farewell"},
    ]

    for spec in template_specs:
        content = MESSAGE_TEMPLATES.get(spec["key"])
        if not content:
            continue
        template_service.create_notification_template(
            name=spec["name"],
            content=content,
            channel=spec["channel"],
            notification_type=spec["notification_type"],
            is_active=True,
        )


def _build_context(store: JsonFileStore | None = None) -> AppContext:
    persistence = store or JsonFileStore()
    trip_repository = TripRepository(store=persistence)
    template_service = TemplateService(store=persistence)
    _seed_concierge_templates(template_service)
    template_service.ensure_default_template()
    preference_service = UserPreferenceService(store=persistence)
    notification_attempt_repository = NotificationAttemptRepository(store=persistence)
    notification_rule_repository = NotificationRuleRepository(store=persistence)
    _seed_default_trips(trip_repository)
    _seed_default_notification_rules(
        notification_rule_repository, template_id=template_service.ensure_default_template().id
    )
    notification_service = NotificationService(attempt_repository=notification_attempt_repository)
    audit_service = AuditService(repository=AuditLogRepository(store=persistence))
    analytics_service = AnalyticsService(
        repository=AnalyticsRepository(store=persistence),
        attempt_repository=notification_attempt_repository,
        trip_repository=trip_repository,
    )
    auth_service = AuthService()
    return AppContext(
        store=persistence,
        auth_service=auth_service,
        trip_repository=trip_repository,
        template_service=template_service,
        preference_service=preference_service,
        notification_attempt_repository=notification_attempt_repository,
        notification_rule_repository=notification_rule_repository,
        notification_service=notification_service,
        audit_service=audit_service,
        analytics_service=analytics_service,
    )


def create_app() -> FastAPI:
    _patch_starlette_router_compat()
    fastapi_app = FastAPI(title="Travel Notification API", version="0.2.0")
    fastapi_app.state.ctx = _build_context()

    security = HTTPBearer(auto_error=False)

    def get_ctx(request: Request) -> AppContext:
        return request.app.state.ctx

    def get_current_user(
        credentials: HTTPAuthorizationCredentials | None = Depends(security),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, str]:
        if credentials is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = ctx.auth_service.authenticate(credentials.credentials)
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user

    def require_admin(user: dict[str, str] = Depends(get_current_user)) -> dict[str, str]:
        if user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin role required")
        return user

    def assert_trip_access(user: dict[str, str], trip: dict[str, Any]) -> None:
        if user.get("role") == "admin":
            return
        if trip.get("user_id") != user.get("id"):
            raise HTTPException(status_code=403, detail="Forbidden")

    @fastapi_app.exception_handler(HTTPException)
    async def _http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        return _error(exc.status_code, str(exc.detail))

    @fastapi_app.exception_handler(RequestValidationError)
    async def _validation_exception_handler(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"code": 422, "error": "Validation error", "detail": exc.errors()},
        )

    @fastapi_app.get("/api/health")
    def get_health() -> dict[str, Any]:
        return _ok({"status": "ok", "time": datetime.now(tz=UTC).isoformat(), "version": "0.2.0"})

    @fastapi_app.get("/api/health/detail")
    def get_health_detail(ctx: AppContext = Depends(get_ctx)) -> dict[str, Any]:
        attempts = ctx.notification_attempt_repository.list_history(limit=9999)
        return _ok(
            {
                "status": "ok",
                "time": datetime.now(tz=UTC).isoformat(),
                "components": {
                    "auth": {"status": "ok", "users": len(ctx.auth_service.users)},
                    "persistence": {"status": "ok", "base_dir": str(ctx.store.base_dir)},
                    "trip_repository": {"status": "ok", "count": len(ctx.trip_repository.list())},
                    "template_repository": {
                        "status": "ok",
                        "count": len(ctx.template_service.list_notification_templates()),
                    },
                    "notification_attempt_repository": {"status": "ok", "count": len(attempts)},
                    "audit_repository": {
                        "status": "ok",
                        "count": len(ctx.audit_service.repository.logs),
                    },
                },
            }
        )

    @fastapi_app.post("/api/auth/login")
    def login(payload: LoginRequest, ctx: AppContext = Depends(get_ctx)) -> dict[str, Any]:
        token = ctx.auth_service.login(payload.username, payload.password)
        if token is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return _ok(token)

    @fastapi_app.post("/api/auth/logout")
    def logout(
        credentials: HTTPAuthorizationCredentials | None = Depends(security),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        if credentials is not None:
            ctx.auth_service.logout(credentials.credentials)
        return {"code": 200}

    @fastapi_app.post("/api/auth/refresh")
    def refresh(payload: RefreshRequest, ctx: AppContext = Depends(get_ctx)) -> dict[str, Any]:
        token = ctx.auth_service.refresh(payload.refresh_token)
        if token is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        return _ok(token)

    @fastapi_app.get("/api/users/me")
    def me(user: dict[str, str] = Depends(get_current_user)) -> dict[str, Any]:
        return _ok(user)

    @fastapi_app.get("/api/preferences/me")
    def get_preferences_me(
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        payload = ctx.preference_service.get_preference_payload(user["id"])
        return _ok(_normalize_preference_payload(payload))

    @fastapi_app.put("/api/preferences/me")
    def update_preferences_me(
        payload: PreferenceUpdateRequest,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        if isinstance(payload.quiet_hours, list) and len(payload.quiet_hours) != 2:
            raise HTTPException(status_code=400, detail="quiet_hours must have 2 integers")
        if isinstance(payload.quiet_hours, dict):
            if "start" not in payload.quiet_hours or "end" not in payload.quiet_hours:
                raise HTTPException(
                    status_code=400, detail="quiet_hours object must contain start/end"
                )
        channels = payload.channels or [PreferenceChannel.EMAIL.value, PreferenceChannel.PUSH.value]
        internal_channels = [_to_internal_preference_channel(item) for item in channels]
        pref = ctx.preference_service.set_preference_from_payload(
            user_id=user["id"],
            channels=internal_channels,
            quiet_hours=payload.quiet_hours,
            max_notifications_per_hour=payload.max_notifications_per_hour,
            auto_escalation=payload.auto_escalation,
            aggregate_notifications=payload.aggregate_notifications,
            allow_marketing=payload.allow_marketing,
        )
        return _ok(_normalize_preference_payload(ctx.preference_service.to_payload(pref)))

    @fastapi_app.get("/api/preferences")
    def get_preferences(
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        return get_preferences_me(user=user, ctx=ctx)

    @fastapi_app.put("/api/preferences")
    def update_preferences(
        payload: PreferenceUpdateRequest,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        return update_preferences_me(payload=payload, user=user, ctx=ctx)

    @fastapi_app.get("/api/templates")
    def list_templates(
        _: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        items = [
            _serialize_template(item) for item in ctx.template_service.list_notification_templates()
        ]
        return _ok({"total": len(items), "items": items})

    @fastapi_app.get("/api/templates/{template_id}")
    def get_template(
        template_id: str,
        _: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        template = ctx.template_service.get_notification_template(template_id)
        if template is None:
            raise HTTPException(status_code=404, detail="Template not found")
        return _ok(_serialize_template(template))

    @fastapi_app.post("/api/templates", status_code=201)
    def create_template(
        payload: TemplateCreateRequest,
        _: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        template = ctx.template_service.create_notification_template(
            name=payload.name,
            content=payload.content,
            channel=_parse_channel(payload.channel).value,
            notification_type=payload.notification_type,
            is_active=payload.is_active,
        )
        return _ok(_serialize_template(template))

    @fastapi_app.put("/api/templates/{template_id}")
    def update_template(
        template_id: str,
        payload: TemplateUpdateRequest,
        _: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        template = ctx.template_service.update_notification_template(
            template_id,
            name=payload.name,
            content=payload.content,
            channel=None if payload.channel is None else _parse_channel(payload.channel).value,
            notification_type=payload.notification_type,
            is_active=payload.is_active,
        )
        if template is None:
            raise HTTPException(status_code=404, detail="Template not found")
        ctx.audit_service.record(
            operator_id="system", action="template_updated", target=template_id, detail={}
        )
        return _ok(_serialize_template(template))

    @fastapi_app.delete("/api/templates/{template_id}")
    def delete_template(
        template_id: str,
        _: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        deleted = ctx.template_service.delete_notification_template(template_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Template not found")
        ctx.audit_service.record(
            operator_id="system", action="template_deleted", target=template_id, detail={}
        )
        return {"code": 200}

    @fastapi_app.get("/api/notifications/templates")
    def list_templates_alias(
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        return list_templates(user, ctx)

    @fastapi_app.post("/api/notifications/templates", status_code=201)
    def create_templates_alias(
        payload: TemplateCreateRequest,
        user: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        return create_template(payload, user, ctx)

    @fastapi_app.put("/api/notifications/templates/{template_id}")
    def update_templates_alias(
        template_id: str,
        payload: TemplateUpdateRequest,
        user: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        return update_template(template_id, payload, user, ctx)

    @fastapi_app.delete("/api/notifications/templates/{template_id}")
    def delete_templates_alias(
        template_id: str,
        user: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        return delete_template(template_id, user, ctx)

    @fastapi_app.get("/api/notifications/rules")
    def list_notification_rules(
        enabled: bool | None = None,
        stage: str | None = None,
        time_slot: str | None = None,
        scene: str | None = None,
        _: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        try:
            items = ctx.notification_rule_repository.list_rules(
                enabled=enabled,
                stage=stage,
                time_slot=time_slot,
                scene=scene,
            )
        except RuleValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _ok_with_message({"total": len(items), "items": items}, "rules listed")

    @fastapi_app.get("/api/notifications/rules/{rule_id}")
    def get_notification_rule(
        rule_id: str,
        _: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        rule = ctx.notification_rule_repository.get_rule(rule_id)
        if rule is None:
            raise HTTPException(status_code=404, detail="Rule not found")
        return _ok_with_message(rule, "rule found")

    @fastapi_app.post("/api/notifications/rules", status_code=201)
    def create_notification_rule(
        payload: NotificationRuleCreateRequest,
        _: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        try:
            rule = ctx.notification_rule_repository.create_rule(payload.model_dump())
        except RuleValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _ok_with_message(rule, "rule created")

    @fastapi_app.put("/api/notifications/rules/{rule_id}")
    def update_notification_rule(
        rule_id: str,
        payload: NotificationRuleUpdateRequest,
        _: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        try:
            rule = ctx.notification_rule_repository.update_rule(
                rule_id, payload.model_dump(exclude_none=True)
            )
        except RuleValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if rule is None:
            raise HTTPException(status_code=404, detail="Rule not found")
        return _ok_with_message(rule, "rule updated")

    @fastapi_app.delete("/api/notifications/rules/{rule_id}")
    def delete_notification_rule(
        rule_id: str,
        _: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        deleted = ctx.notification_rule_repository.delete_rule(rule_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Rule not found")
        return _ok_with_message({"deleted": True, "id": rule_id}, "rule deleted")

    @fastapi_app.get("/api/trips")
    def list_trips(
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        items = ctx.trip_repository.list()
        if user.get("role") != "admin":
            items = [item for item in items if item.get("user_id") == user.get("id")]
        normalized_items = [_serialize_trip(item) for item in items]
        return _ok({"total": len(normalized_items), "items": normalized_items})

    def create_trip_record(
        *,
        payload: TripCreateRequest,
        user: dict[str, str],
        ctx: AppContext,
    ) -> dict[str, Any]:
        team_id = _resolve_team_id(payload.team, payload.team_id)
        if not team_id:
            raise HTTPException(status_code=400, detail="Missing required field: team or team_id")
        trip_id = f"trip-{uuid4().hex[:8]}"
        now = datetime.now(tz=UTC).isoformat()
        trip = {
            "id": trip_id,
            "destination": payload.destination,
            "team": team_id,
            "team_id": team_id,
            "start_date": payload.start_date,
            "end_date": payload.end_date,
            "participants": payload.participants,
            "status": _normalize_trip_status(payload.status),
            "user_id": user["id"],
            "created_at": now,
            "updated_at": now,
        }
        ctx.trip_repository.create(trip)

        template = next(
            (item for item in ctx.template_service.list_notification_templates() if item.is_active),
            ctx.template_service.ensure_default_template(),
        )
        rendered = ctx.template_service.render_notification(
            template,
            {
                "customer_name": user.get("username", user["id"]),
                "destination": payload.destination,
            },
        )
        task = NotificationTask(
            team_id=team_id,
            trip_id=trip_id,
            customer_id=user["id"],
            rendered_content=rendered,
            idempotency_key=f"{trip_id}:created",
            primary_channel=Channel.SMS,
            fallback_channel=Channel.WECHAT_WORK_GROUP,
        )
        dispatch_result = ctx.notification_service.dispatch(task)
        ctx.audit_service.record(
            operator_id=user["id"],
            action="trip_created",
            target=trip_id,
            detail={"destination": payload.destination, "team_id": team_id},
        )
        ctx.audit_service.record(
            operator_id=user["id"],
            action="notification_dispatched",
            target=trip_id,
            detail={"ok": dispatch_result["ok"], "attempts": len(task.attempts)},
        )
        return {
            "trip": _serialize_trip(trip),
            "notification": {
                "ok": dispatch_result["ok"],
                "status": task.status.value,
                "attempt_count": len(task.attempts),
            },
        }

    @fastapi_app.post("/api/trips", status_code=201)
    def create_trip(
        payload: TripCreateRequest,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        created = create_trip_record(payload=payload, user=user, ctx=ctx)
        return _ok(created)

    @fastapi_app.post("/api/trips/import")
    async def import_trips(
        file: UploadFile = File(...),
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        filename = (file.filename or "").lower()
        raw = await file.read()
        if not raw:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        if filename.endswith(".csv"):
            parsed_rows = _read_csv_rows(raw)
        elif filename.endswith(".xlsx"):
            parsed_rows = _read_xlsx_rows(raw)
        else:
            raise HTTPException(status_code=400, detail="Only .csv and .xlsx files are supported")

        created_items: list[dict[str, Any]] = []
        skipped = 0
        for row in parsed_rows:
            destination = _extract_import_field(row, ["destination", "目的地", "行程名称"])
            team_id = _extract_import_field(row, ["team_id", "team", "teamid", "团队ID", "团队"])
            start_date = _extract_import_field(row, ["start_date", "startdate", "开始日期", "开始时间"])
            end_date = _extract_import_field(row, ["end_date", "enddate", "结束日期", "结束时间"])
            participants_text = _extract_import_field(row, ["participants", "人数", "参与人数"])
            try:
                participants = int(float(participants_text)) if participants_text else 0
            except ValueError:
                participants = 0

            if not destination or not team_id or not start_date or not end_date:
                skipped += 1
                continue

            trip_payload = TripCreateRequest(
                destination=destination,
                team=team_id,
                start_date=_normalize_excel_serial_date(start_date),
                end_date=_normalize_excel_serial_date(end_date),
                participants=max(participants, 0),
                status="计划中",
            )
            created = create_trip_record(payload=trip_payload, user=user, ctx=ctx)
            created_items.append(created["trip"])

        return _ok(
            {
                "created_count": len(created_items),
                "skipped_count": skipped,
                "items": created_items,
            }
        )

    @fastapi_app.put("/api/trips/{trip_id}")
    def update_trip(
        trip_id: str,
        payload: TripUpdateRequest,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        existing = ctx.trip_repository.get(trip_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Trip not found")
        assert_trip_access(user, existing)

        patch = payload.model_dump(exclude_none=True)
        if "team_id" in patch or "team" in patch:
            normalized_team_id = _resolve_team_id(
                patch.get("team") if isinstance(patch.get("team"), str) else None,
                patch.get("team_id") if isinstance(patch.get("team_id"), str) else None,
            )
            if not normalized_team_id:
                raise HTTPException(status_code=400, detail="team/team_id cannot be empty")
            patch["team_id"] = normalized_team_id
            patch["team"] = normalized_team_id
        if "status" in patch and isinstance(patch["status"], str):
            patch["status"] = _normalize_trip_status(patch["status"])
        updated = ctx.trip_repository.update(trip_id, patch)
        if updated is None:
            raise HTTPException(status_code=404, detail="Trip not found")
        ctx.audit_service.record(
            operator_id=user["id"], action="trip_updated", target=trip_id, detail=patch
        )
        return _ok(_serialize_trip(updated))

    @fastapi_app.delete("/api/trips/{trip_id}")
    def delete_trip(
        trip_id: str,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        existing = ctx.trip_repository.get(trip_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Trip not found")
        assert_trip_access(user, existing)
        ctx.trip_repository.delete(trip_id)
        ctx.audit_service.record(
            operator_id=user["id"], action="trip_deleted", target=trip_id, detail={}
        )
        return {"code": 200}

    @fastapi_app.post("/api/notifications/send")
    def send_notification(
        payload: NotificationSendRequest,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        template = None
        if payload.template_id:
            template = ctx.template_service.get_notification_template(payload.template_id)
            if template is None:
                raise HTTPException(status_code=404, detail="Template not found")
        if template is None:
            template = next(
                (
                    item
                    for item in ctx.template_service.list_notification_templates()
                    if item.is_active
                ),
                ctx.template_service.ensure_default_template(),
            )

        destination = payload.destination or "未指定行程"
        team_id = _resolve_team_id(payload.team, payload.team_id)
        if payload.trip_id:
            trip = ctx.trip_repository.get(payload.trip_id)
            if trip is not None:
                destination = trip.get("destination", destination)
                team_id = str(trip.get("team_id") or trip.get("team") or team_id)

        rendered = ctx.template_service.render_notification(
            template,
            {
                "customer_name": payload.customer_name or user.get("username", user["id"]),
                "destination": destination,
            },
        )
        task = NotificationTask(
            team_id=team_id,
            trip_id=payload.trip_id or "",
            customer_id=user["id"],
            rendered_content=rendered,
            idempotency_key=f"manual:{uuid4().hex}",
            primary_channel=_parse_channel(payload.channel),
            fallback_channel=Channel.WECHAT_WORK_GROUP,
        )
        dispatch_result = ctx.notification_service.dispatch(task)
        ctx.audit_service.record(
            operator_id=user["id"],
            action="notification_dispatched",
            target=payload.trip_id or "manual",
            detail={"ok": dispatch_result["ok"], "attempts": len(task.attempts)},
        )
        return _ok(
            {
                "ok": dispatch_result["ok"],
                "notification_id": task.id,
                "status": task.status.value,
            }
        )

    @fastapi_app.get("/api/notifications/history")
    def notification_history(
        limit: int = 20,
        trip_id: str | None = None,
        team_id: str | None = None,
        team: str | None = None,
        channel: str | None = None,
        status: str | None = None,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        customer_id = None if user.get("role") == "admin" else user["id"]
        resolved_team_id = _resolve_team_id(team, team_id)
        items = _query_notification_items(
            repository=ctx.notification_attempt_repository,
            limit=limit,
            trip_id=trip_id,
            team_id=resolved_team_id or None,
            customer_id=customer_id,
            channel=channel,
            status=status,
        )
        return _ok({"total": len(items), "items": items})

    @fastapi_app.get("/api/notifications/recent")
    def recent_notifications(
        limit: int = 10,
        trip_id: str | None = None,
        team_id: str | None = None,
        team: str | None = None,
        channel: str | None = None,
        status: str | None = None,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        customer_id = None if user.get("role") == "admin" else user["id"]
        resolved_team_id = _resolve_team_id(team, team_id)
        items = _query_notification_items(
            repository=ctx.notification_attempt_repository,
            limit=limit,
            trip_id=trip_id,
            team_id=resolved_team_id or None,
            customer_id=customer_id,
            channel=channel,
            status=status,
        )
        recent = [_to_recent_item(item) for item in items]
        return _ok({"total": len(recent), "items": recent})

    @fastapi_app.get("/api/trips/{trip_id}/timeline")
    def trip_timeline(
        trip_id: str,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        trip = ctx.trip_repository.get(trip_id)
        if trip is None:
            raise HTTPException(status_code=404, detail="Trip not found")
        assert_trip_access(user, trip)
        customer_id = None if user.get("role") == "admin" else user["id"]
        attempts = _query_notification_items(
            repository=ctx.notification_attempt_repository,
            limit=200,
            trip_id=trip_id,
            team_id=None,
            customer_id=customer_id,
        )
        logs = ctx.audit_service.repository.list_by_target_payload(trip_id)
        return _ok(
            {"trip": _serialize_trip(trip), "notification_attempts": attempts, "audit_logs": logs}
        )

    @fastapi_app.get("/api/dashboard/stats")
    def dashboard_stats(
        _: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        attempts = ctx.notification_attempt_repository.list_history(limit=9999)
        sent = sum(1 for item in attempts if item.get("ok") is True)
        total = len(attempts)
        return _ok(
            {
                "today_notifications": total,
                "active_trips": len(
                    [t for t in ctx.trip_repository.list() if t.get("status") != "已完成"]
                ),
                "total_users": len(ctx.auth_service.users),
                "pending_complaints": 0,
                "notification_success_rate": round((sent / total) * 100, 1) if total else 0.0,
            }
        )

    @fastapi_app.get("/api/analytics/metrics")
    def analytics_metrics(
        _: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        return _ok(ctx.analytics_service.build_metrics_snapshot())

    return fastapi_app


app = create_app()


def reset_state(purge_persistence: bool = False) -> None:
    store = JsonFileStore()
    if purge_persistence:
        store.clear_all()
    app.state.ctx = _build_context(store=store)


def dispatch_request(
    method: str, path: str, headers: dict[str, str] | None = None, body: str = ""
) -> Response:
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.request(method, path, headers=headers or {}, data=body)
    payload: dict[str, Any]
    if response.content:
        payload = response.json()
    else:
        payload = {"code": response.status_code}
    return Response(status=response.status_code, body=payload)


def run_http_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    uvicorn.run(app, host=host, port=port)
