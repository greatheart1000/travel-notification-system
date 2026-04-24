from __future__ import annotations

import csv
import io
import os
import re
import zipfile
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import uuid4
from xml.etree import ElementTree

import uvicorn
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator
from starlette.routing import Router as StarletteRouter

from app.core.entities import Channel as PreferenceChannel
from app.core.models import Channel
from app.modules.analytics.service import AnalyticsRepository, AnalyticsService
from app.modules.audit.service import AuditLogRepository, AuditService
from app.modules.integration.auth import AuthService
from app.modules.integration.persistence import (
    JsonFileStore,
    ProjectNotificationConfigRepository,
    TripRepository,
)
from app.modules.integration.rbac import PermissionDenied, assert_tenant_scope, require_permission
from app.modules.integration.weather_provider import WeatherProvider
from app.modules.notification.concierge_playbook import MESSAGE_TEMPLATES
from app.modules.notification.idempotency import IdempotencyStore
from app.modules.notification.models import NotificationTask
from app.modules.notification.rule_service import NotificationRuleRepository, RuleValidationError
from app.modules.notification.service import NotificationAttemptRepository, NotificationService
from app.modules.trigger.risk_alert_service import RiskAlertService
from app.services.analytics_view_service import AnalyticsViewService
from app.services.async_dispatch import AsyncDispatchService
from app.services.dashboard_service import DashboardService
from app.services.emergency_weather_service import EmergencyWeatherService
from app.services.notification_agent_service import NotificationAgentService
from app.services.preference_service import UserPreferenceService
from app.services.scheduler_service import init_scheduler
from app.services.template_service import TemplateService
from app.services.workflow_orchestrator import WorkflowOrchestrator

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
    project_notification_config_repository: ProjectNotificationConfigRepository
    template_service: TemplateService
    preference_service: UserPreferenceService
    notification_attempt_repository: NotificationAttemptRepository
    notification_rule_repository: NotificationRuleRepository
    notification_service: NotificationService
    async_dispatch_service: AsyncDispatchService
    audit_service: AuditService
    analytics_service: AnalyticsService
    weather_provider: WeatherProvider
    notification_tasks: dict[str, NotificationTask]


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
    project_id: str = ""
    stage: str = ""
    time_slot: str = ""
    scene: str = ""
    sms_sign_name: str = ""
    provider_template_code: str = ""


class TemplateUpdateRequest(BaseModel):
    name: str | None = None
    content: str | None = None
    channel: str | None = None
    notification_type: str | None = None
    is_active: bool | None = None
    project_id: str | None = None
    stage: str | None = None
    time_slot: str | None = None
    scene: str | None = None
    sms_sign_name: str | None = None
    provider_template_code: str | None = None


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


class RuleReviewRequest(BaseModel):
    comment: str | None = None


class RuleRejectRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=200)


class RuleSimulationRequest(BaseModel):
    stage: str
    time_slot: str
    scene: str
    context: dict[str, Any] = Field(default_factory=dict)


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
    leader_name: str | None = None
    contact_phone: str | None = None
    itinerary: list[dict[str, Any]] | None = None
    guests: list[dict[str, Any]] | None = None

    @field_validator("team", "team_id", "leader_name", "contact_phone")
    @classmethod
    def validate_team_fields(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return value.strip()


class TripImportValidationApplyRequest(BaseModel):
    fields: dict[str, str] = Field(default_factory=dict)


class NotificationSendRequest(BaseModel):
    template_id: str | None = None
    trip_id: str | None = None
    trip: str | None = None
    team: str | None = None
    team_id: str | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    custom_content: str | None = None
    destination: str | None = None
    channel: str = "sms"
    async_delivery: bool = False


class EmergencyWeatherSendRequest(BaseModel):
    alert_id: str
    custom_content: str | None = None
    channel: str = "sms"


class DispatchPreviewRequest(BaseModel):
    trip_id: str
    node_key: str
    channel: str = "sms"
    channel_code: str | None = None
    template_id: str | None = None


class DispatchNowRequest(BaseModel):
    trip_id: str
    node_key: str
    channel: str = "sms"
    channel_code: str | None = None
    template_id: str | None = None
    content: str | None = None


class RetryDispatchRequest(BaseModel):
    reason: str | None = None


class AssignTakeoverRequest(BaseModel):
    task_id: str
    assignee_user_id: str
    assignee_name: str | None = None
    deadline_at: str | None = None
    note: str | None = None


class CompleteWorkbenchTaskRequest(BaseModel):
    result_note: str | None = None
    evidence_type: str | None = None
    evidence_ref: str | None = None


class NudgeWorkbenchTaskRequest(BaseModel):
    target_role: str | None = None
    message: str | None = None


class AgentNotificationDraftRequest(BaseModel):
    route: str
    travel_stage: str
    time_node: str
    core_work: str
    action_detail: str = ""
    project_id: str = ""
    channel: str = "sms"
    notification_type: str = "daily_reminder"
    save_as_templates: bool = True
    template_prefix: str = "Agent自动生成"


class DailyNotificationGenerateRequest(BaseModel):
    group_id: str
    date: str
    weather: str = "多云"
    core_work: str = "时段性专属温馨提示"
    save_as_templates: bool = False
    channel: str = "sms"
    project_id: str = ""


class ProjectNotificationConfigUpsertRequest(BaseModel):
    project_name: str = ""
    weather_enabled: bool = True
    qweather_credential_id: str = ""
    qweather_location_id: str = ""
    qweather_lat: str = ""
    qweather_lon: str = ""
    weather_alert_thresholds: dict[str, Any] = Field(default_factory=dict)
    sms_provider: str = "aliyun"
    sms_sign_name: str = ""
    sms_template_code_normal: str = ""
    sms_template_code_weather_alert: str = ""
    manual_takeover_target: str = ""


def _ok(data: Any) -> dict[str, Any]:
    return {"code": 200, "data": data}


def _error(status: int, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"code": status, "error": message, "detail": message},
    )


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
    workbook_rows = _read_xlsx_workbook_rows(raw)
    if not workbook_rows:
        return []
    _, first_sheet_rows = next(iter(workbook_rows.items()))
    return first_sheet_rows


def _read_xlsx_workbook_rows(raw: bytes) -> dict[str, list[dict[str, str]]]:
    workbook_rows: dict[str, list[dict[str, str]]] = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        workbook_xml = archive.read("xl/workbook.xml")
        workbook = ElementTree.fromstring(workbook_xml)
        namespaces = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        workbook_rels = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_namespaces = {"rel": "http://schemas.openxmlformats.org/package/2006/relationships"}
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared_root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in shared_root.findall(
                ".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si"
            ):
                text = "".join(
                    node.text or ""
                    for node in item.findall(
                        ".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"
                    )
                )
                shared_strings.append(text)

        for sheet in workbook.findall("main:sheets/main:sheet", namespaces):
            name = str(sheet.attrib.get("name") or "").strip()
            relation_id = sheet.attrib.get(
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
            )
            if not name or relation_id is None:
                continue
            rel = workbook_rels.find(f"rel:Relationship[@Id='{relation_id}']", rel_namespaces)
            if rel is None:
                continue
            target = rel.attrib.get("Target", "")
            worksheet_path = f"xl/{target}" if not target.startswith("xl/") else target
            rows = _read_xlsx_sheet_rows(
                archive=archive,
                worksheet_path=worksheet_path,
                shared_strings=shared_strings,
            )
            workbook_rows[name] = rows
    return workbook_rows


def _read_xlsx_sheet_rows(
    *,
    archive: zipfile.ZipFile,
    worksheet_path: str,
    shared_strings: list[str],
) -> list[dict[str, str]]:
    worksheet = ElementTree.fromstring(archive.read(worksheet_path))
    parsed_rows: list[list[str]] = []
    for row_node in worksheet.findall(
        ".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"
    ):
        cells: dict[int, str] = {}
        for cell in row_node.findall(
            "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"
        ):
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
                    shared_strings[shared_index] if 0 <= shared_index < len(shared_strings) else ""
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


def _find_workbook_sheet(
    workbook_rows: dict[str, list[dict[str, str]]], names: set[str]
) -> list[dict[str, str]]:
    for sheet_name, rows in workbook_rows.items():
        normalized = _normalize_import_header(sheet_name)
        if normalized in names:
            return rows
    return []


def _build_structured_trip_import(
    workbook_rows: dict[str, list[dict[str, str]]],
) -> dict[str, Any] | None:
    itinerary_rows = _find_workbook_sheet(workbook_rows, {"行程表", "itinerary"})
    guest_rows = _find_workbook_sheet(workbook_rows, {"客人表", "guests"})
    if not itinerary_rows:
        return None

    first_row = itinerary_rows[0]
    team_id = _extract_import_field(first_row, ["team_id", "team", "团号"])
    destination = _extract_import_field(first_row, ["destination", "目的地", "行程名称", "线路"])
    start_date = _normalize_excel_serial_date(
        _extract_import_field(first_row, ["start_date", "出发日期", "出团日期"])
    )
    end_date = _normalize_excel_serial_date(
        _extract_import_field(first_row, ["end_date", "结束日期", "回程日期"])
    )
    if not team_id or not destination or not start_date or not end_date:
        return None

    itinerary: list[dict[str, str]] = []
    for row in itinerary_rows:
        itinerary.append(
            {
                "date": _normalize_excel_serial_date(_extract_import_field(row, ["date", "日期"])),
                "route": _extract_import_field(row, ["route", "路线", "行程"]),
                "transport": _extract_import_field(row, ["transport", "交通"]),
                "hotel": _extract_import_field(row, ["hotel", "酒店"]),
            }
        )

    guests: list[dict[str, str]] = []
    for row in guest_rows:
        name = _extract_import_field(row, ["name", "姓名", "客人姓名"])
        phone = _extract_import_field(row, ["phone", "手机号", "电话"])
        notes = _extract_import_field(row, ["notes", "备注", "特殊要求"])
        if not any((name, phone, notes)):
            continue
        guests.append({"name": name, "phone": phone, "notes": notes})

    return {
        "team_id": team_id,
        "destination": destination,
        "start_date": start_date,
        "end_date": end_date,
        "participants": len(guests),
        "itinerary": itinerary,
        "guests": guests,
    }


def _build_trip_import_snapshot(
    trip: dict[str, Any], execution_row: dict[str, Any] | None = None
) -> dict[str, Any]:
    serialized = _serialize_trip(trip)
    itinerary = serialized.get("itinerary", [])
    guests = serialized.get("guests", [])
    has_itinerary = len(itinerary) > 0
    has_guests = len(guests) > 0
    has_guest_phone = any(str(item.get("phone") or "").strip() for item in guests)
    has_leader_contact = bool(str(serialized.get("contact_phone") or "").strip())

    recognized_fields = [
        {"key": "team_id", "label": "团号", "value": serialized.get("team_id", "") or "未识别"},
        {
            "key": "destination",
            "label": "线路",
            "value": serialized.get("destination", "") or "未识别",
        },
        {
            "key": "start_date",
            "label": "出团日期",
            "value": serialized.get("start_date", "") or "未识别",
        },
        {
            "key": "end_date",
            "label": "回程日期",
            "value": serialized.get("end_date", "") or "未识别",
        },
        {
            "key": "participants",
            "label": "人数",
            "value": str(serialized.get("participants") or 0),
        },
        {
            "key": "itinerary",
            "label": "每日行程",
            "value": f"{len(itinerary)} 天" if has_itinerary else "未识别",
        },
        {
            "key": "guests",
            "label": "客人名单",
            "value": f"{len(guests)} 人" if has_guests else "未识别",
        },
    ]
    pending_fields = [
        {"key": "transport_mapping", "label": "交通工具映射", "value": "待确认"},
        {"key": "meal_symbols", "label": "早午晚符号解析", "value": "待确认"},
    ]
    missing_fields: list[dict[str, str]] = []
    if not has_guest_phone:
        missing_fields.append({"key": "guest_phone", "label": "游客联系方式"})
    if not has_leader_contact:
        missing_fields.append({"key": "leader_phone", "label": "领队电话"})

    import_ready_count = len([item for item in recognized_fields if item["value"] != "未识别"])
    import_total = len(recognized_fields) + len(pending_fields) + len(missing_fields)
    completeness = round((import_ready_count / max(import_total, 1)) * 100)

    itinerary_digest = [
        {
            "date": str(item.get("date") or ""),
            "transport": str(item.get("transport") or "待补全"),
            "route": str(item.get("route") or "待补全"),
            "hotel": str(item.get("hotel") or "待补全"),
            "meal": "早:待确认 午:待确认 晚:待确认",
        }
        for item in itinerary
    ]
    guest_digest = [
        {
            "name": str(item.get("name") or "未命名游客"),
            "phone": str(item.get("phone") or "待补录电话"),
            "status": "可通知" if str(item.get("phone") or "").strip() else "待补全",
        }
        for item in guests
    ]
    pickup_digest: list[dict[str, str]] = []
    for index, item in enumerate(itinerary[:2]):
        route = str(item.get("route") or "")
        route_stops = _split_route_stops(route)
        from_stop = route_stops[0] if route_stops else "机场"
        to_stop = route_stops[-1] if route_stops else "酒店"
        trip_date = str(item.get("date") or "")
        pickup_digest.append(
            {
                "type": "接",
                "date": trip_date,
                "location": f"{from_stop}接站口",
                "shift": f"航班待补录-{index + 1}",
                "note": "来源于导入行程，需人工确认班次",
            }
        )
        pickup_digest.append(
            {
                "type": "送",
                "date": trip_date,
                "location": f"{to_stop}送站点",
                "shift": f"返程待补录-{index + 1}",
                "note": "来源于导入行程，需人工确认班次",
            }
        )
    return {
        "trip_id": serialized.get("id", ""),
        "completeness": completeness,
        "has_itinerary": has_itinerary,
        "has_guests": has_guests,
        "today_todo": int((execution_row or {}).get("todo_count", 0)),
        "next_node": (execution_row or {}).get("next_node_due_at")
        or (execution_row or {}).get("dispatch_status")
        or "待生成通知节点",
        "recognized_fields": recognized_fields,
        "pending_fields": pending_fields,
        "missing_fields": missing_fields,
        "itinerary_digest": itinerary_digest,
        "guest_digest": guest_digest,
        "pickup_digest": pickup_digest,
    }


def _serialize_trip(trip: dict[str, Any]) -> dict[str, Any]:
    resolved_team_id = str(trip.get("team_id") or trip.get("team") or "")
    itinerary = trip.get("itinerary") if isinstance(trip.get("itinerary"), list) else []
    guests = trip.get("guests") if isinstance(trip.get("guests"), list) else []
    participants = int(trip.get("participants", 0) or 0)
    if guests:
        participants = len(guests)
    return {
        "id": trip.get("id", ""),
        "destination": trip.get("destination", ""),
        "team_id": resolved_team_id,
        "team": resolved_team_id,
        "start_date": trip.get("start_date", ""),
        "end_date": trip.get("end_date", ""),
        "participants": participants,
        "status": _normalize_trip_status(str(trip.get("status", "planned"))),
        "leader_name": str(trip.get("leader_name") or ""),
        "contact_phone": str(trip.get("contact_phone") or ""),
        "itinerary": itinerary,
        "guests": guests,
        "user_id": trip.get("user_id", ""),
        "tenant_id": trip.get("tenant_id", ""),
        "created_at": trip.get("created_at"),
        "updated_at": trip.get("updated_at"),
    }


def _split_route_stops(route: str) -> list[str]:
    normalized = route.replace("→", "->").replace("—", "->").replace("－", "->").replace("至", "->")
    parts = [segment.strip() for segment in normalized.split("->")]
    return [segment for segment in parts if segment]


def _derive_route_summary(itinerary: list[dict[str, Any]]) -> list[str]:
    ordered: list[str] = []
    for item in itinerary:
        for stop in _split_route_stops(str(item.get("route") or "")):
            if stop not in ordered:
                ordered.append(stop)
    return ordered


def _derive_trip_leader(guests: list[dict[str, Any]]) -> dict[str, str]:
    for guest in guests:
        notes = str(guest.get("notes") or "")
        if "领队" in notes:
            return {
                "name": str(guest.get("name") or ""),
                "phone": str(guest.get("phone") or ""),
                "notes": notes,
            }
    if guests:
        first = guests[0]
        return {
            "name": str(first.get("name") or ""),
            "phone": str(first.get("phone") or ""),
            "notes": str(first.get("notes") or ""),
        }
    return {"name": "", "phone": "", "notes": ""}


def _derive_trip_day_segments(itinerary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    days: list[dict[str, Any]] = []
    for index, item in enumerate(itinerary, start=1):
        route = str(item.get("route") or "")
        hotel = str(item.get("hotel") or "")
        transport = str(item.get("transport") or "")
        days.append(
            {
                "day": index,
                "title": f"Day {index}",
                "date": str(item.get("date") or ""),
                "route": route,
                "segments": [
                    {
                        "departure_time": "",
                        "arrival_time": "",
                        "from": _split_route_stops(route)[0] if _split_route_stops(route) else "",
                        "to": _split_route_stops(route)[-1] if _split_route_stops(route) else "",
                        "transport": transport,
                        "sightseeing": route,
                        "hotel": hotel,
                        "meal_plan": "",
                    }
                ],
                "hotel": hotel,
                "transport": transport,
            }
        )
    return days


def _serialize_trip_schedule(
    trip: dict[str, Any], notification_items: list[dict[str, Any]]
) -> dict[str, Any]:
    serialized_trip = _serialize_trip(trip)
    itinerary = serialized_trip.get("itinerary", [])
    guests = serialized_trip.get("guests", [])
    derived_leader = _derive_trip_leader(guests)
    leader_name = str(serialized_trip.get("leader_name") or "").strip()
    contact_phone = str(serialized_trip.get("contact_phone") or "").strip()
    leader = {
        "name": leader_name or derived_leader.get("name", ""),
        "phone": contact_phone or derived_leader.get("phone", ""),
        "notes": derived_leader.get("notes", ""),
    }
    route_summary = _derive_route_summary(itinerary)
    next_notification_hint = ""
    status_code = str(serialized_trip.get("status") or "planned")
    if status_code == "planned":
        next_notification_hint = "建议发送行前通知"
    elif status_code == "in_progress":
        next_notification_hint = "建议发送下一条行中提醒"
    elif status_code == "completed":
        next_notification_hint = "可发送行后回访问卷"

    latest_notification = notification_items[0] if notification_items else None
    return {
        "trip_id": serialized_trip["id"],
        "team_id": serialized_trip["team_id"],
        "destination": serialized_trip["destination"],
        "start_date": serialized_trip["start_date"],
        "end_date": serialized_trip["end_date"],
        "traveler_count": int(serialized_trip.get("participants", 0) or 0),
        "status": {
            "code": status_code,
            "label": str(serialized_trip.get("status") or ""),
        },
        "leader": leader,
        "contact": {
            "name": leader["name"],
            "phone": leader["phone"],
        },
        "route_summary": route_summary,
        "days": _derive_trip_day_segments(itinerary),
        "notification_summary": {
            "recent_count": len(notification_items),
            "latest": latest_notification,
            "next_hint": next_notification_hint,
        },
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
        "tenant_id": item.get("tenant_id", ""),
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
        "customer_name": str(item.get("customer_name") or normalized["customer_id"]),
        "trip": str(item.get("trip_label") or normalized["trip_id"]),
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
    tenant_id: str | None = None,
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
    if tenant_id:
        normalized = [item for item in normalized if item["tenant_id"] == tenant_id]
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
        "tenant_id": getattr(template, "tenant_id", ""),
        "project_id": getattr(template, "project_id", ""),
        "notification_type": template.notification_type.value,
        "channel": template.channel.value,
        "stage": getattr(template, "stage", ""),
        "time_slot": getattr(template, "time_slot", ""),
        "scene": getattr(template, "scene", ""),
        "sms_sign_name": getattr(template, "sms_sign_name", ""),
        "provider_template_code": getattr(template, "provider_template_code", ""),
        "status": status,
        "enabled": template.is_active,
        "template": template.content,
        "content": template.content,
        "is_active": template.is_active,
        "created_at": template.created_at,
        "updated_at": template.updated_at,
    }


def _serialize_project_notification_config(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "tenant_id": str(payload.get("tenant_id") or ""),
        "project_id": str(payload.get("project_id") or ""),
        "project_name": str(payload.get("project_name") or ""),
        "weather_enabled": bool(payload.get("weather_enabled", True)),
        "qweather_credential_id": str(payload.get("qweather_credential_id") or ""),
        "qweather_location_id": str(payload.get("qweather_location_id") or ""),
        "qweather_lat": str(payload.get("qweather_lat") or ""),
        "qweather_lon": str(payload.get("qweather_lon") or ""),
        "weather_alert_thresholds": payload.get("weather_alert_thresholds") or {},
        "sms_provider": str(payload.get("sms_provider") or "aliyun"),
        "sms_sign_name": str(payload.get("sms_sign_name") or ""),
        "sms_template_code_normal": str(payload.get("sms_template_code_normal") or ""),
        "sms_template_code_weather_alert": str(
            payload.get("sms_template_code_weather_alert") or ""
        ),
        "manual_takeover_target": str(payload.get("manual_takeover_target") or ""),
        "created_at": payload.get("created_at"),
        "updated_at": payload.get("updated_at"),
    }


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _parse_missing_fields(error: Exception) -> list[str]:
    message = str(error)
    marker = "missing_template_variables:"
    if marker not in message:
        return []
    suffix = message.split(marker, maxsplit=1)[1]
    return [item.strip() for item in suffix.split(",") if item.strip()]


def _default_workbench_nodes_for_trip(trip: dict[str, Any]) -> list[dict[str, str]]:
    status = _normalize_trip_status(str(trip.get("status", "planned")))
    if status == "planned":
        return [
            {
                "stage": "pre_trip_t3",
                "node_key": "pre_trip_t3_flight_check",
                "title": "出发前3天航班确认与温馨提示",
                "risk_level": "medium",
            },
            {
                "stage": "pre_trip_t1",
                "node_key": "pre_trip_t1_insurance_check",
                "title": "出发前1天保险核查与建群检查",
                "risk_level": "high",
            },
        ]
    if status == "in_progress":
        return [
            {
                "stage": "on_trip_daily",
                "node_key": "daily_morning",
                "title": "行程中早间提醒",
                "risk_level": "medium",
            },
            {
                "stage": "on_trip_daily",
                "node_key": "daily_evening",
                "title": "行程中晚间次日预告",
                "risk_level": "medium",
            },
        ]
    return [
        {
            "stage": "post_trip_followup",
            "node_key": "post_trip_farewell",
            "title": "下团欢送与满意度回访",
            "risk_level": "low",
        }
    ]


def _ensure_workbench_tasks(
    ctx: AppContext, *, tenant_id: str, owner_scope: str | None = None
) -> list[dict[str, Any]]:
    records = ctx.store.read_collection("workbench_tasks")
    tasks = [item for item in records if str(item.get("tenant_id") or "") == tenant_id]
    existing_keys = {
        (str(item.get("trip_id") or ""), str(item.get("node_key") or "")) for item in tasks
    }
    now = datetime.now(tz=UTC)
    changed = False
    for trip in ctx.trip_repository.list():
        if str(trip.get("tenant_id") or "") != tenant_id:
            continue
        owner_id = str(trip.get("user_id") or "admin")
        if owner_scope == "mine" and owner_id == "":
            continue
        trip_id = str(trip.get("id") or "")
        for offset, node in enumerate(_default_workbench_nodes_for_trip(trip), start=1):
            dedupe_key = (trip_id, node["node_key"])
            if dedupe_key in existing_keys:
                continue
            due_at = (now + timedelta(hours=offset)).isoformat()
            tasks.append(
                {
                    "id": f"task-{uuid4().hex[:10]}",
                    "tenant_id": tenant_id,
                    "trip_id": trip_id,
                    "trip_name": str(trip.get("destination") or trip_id),
                    "team_id": str(trip.get("team_id") or trip.get("team") or ""),
                    "stage": node["stage"],
                    "node_key": node["node_key"],
                    "title": node["title"],
                    "due_at": due_at,
                    "owner_id": owner_id,
                    "owner_role": "concierge",
                    "owner_name": owner_id,
                    "priority": "p0" if node["risk_level"] == "high" else "p1",
                    "risk_level": node["risk_level"],
                    "status": "todo",
                    "dispatch_id": "",
                    "created_at": _now_iso(),
                    "updated_at": _now_iso(),
                }
            )
            existing_keys.add(dedupe_key)
            changed = True
    if changed:
        untouched = [item for item in records if str(item.get("tenant_id") or "") != tenant_id]
        ctx.store.write_collection("workbench_tasks", untouched + tasks)
    return tasks


def _save_workbench_tasks(ctx: AppContext, tenant_id: str, tasks: list[dict[str, Any]]) -> None:
    records = ctx.store.read_collection("workbench_tasks")
    untouched = [item for item in records if str(item.get("tenant_id") or "") != tenant_id]
    ctx.store.write_collection("workbench_tasks", untouched + tasks)


def _task_status_for_due(task: dict[str, Any]) -> str:
    status = str(task.get("status") or "todo")
    if status in {"done", "handover_in_progress"}:
        return status
    due_at = str(task.get("due_at") or "")
    try:
        due = datetime.fromisoformat(due_at.replace("Z", "+00:00"))
    except ValueError:
        return status
    return "overdue" if due < datetime.now(tz=UTC) else status


def _seed_default_trips(trip_repository: TripRepository) -> None:
    now = datetime.now(tz=UTC).isoformat()
    existing_trip_ids = {str(item.get("id") or "") for item in trip_repository.list()}
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
            "user_id": "user-001",
            "tenant_id": "tenant-a",
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
            "user_id": "user-001",
            "tenant_id": "tenant-a",
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
            "user_id": "user-001",
            "tenant_id": "tenant-a",
            "created_at": now,
            "updated_at": now,
        },
    ]
    for trip in default_trips:
        if str(trip.get("id") or "") in existing_trip_ids:
            continue
        trip_repository.create(trip)


def _seed_default_notification_rules(
    rule_repository: NotificationRuleRepository, template_id: str, tenant_id: str
) -> None:
    if rule_repository.list_rules(tenant_id=tenant_id):
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
        rule["tenant_id"] = tenant_id
        rule_repository.create_rule(rule)


def _seed_concierge_templates(template_service: TemplateService, tenant_id: str) -> None:
    if template_service.list_notification_templates(tenant_id=tenant_id):
        return

    template_specs: list[dict[str, str]] = [
        {
            "name": "行前3天-航班与行前提示",
            "key": "pre_flight_notice",
            "channel": "wechat_work_group",
            "notification_type": "pre_trip_reminder",
            "stage": "pre_trip",
            "time_slot": "morning",
            "scene": "normal",
        },
        {
            "name": "行前1天-入群欢迎词",
            "key": "group_welcome",
            "channel": "wechat_work_group",
            "notification_type": "pre_trip_reminder",
            "stage": "pre_trip",
            "time_slot": "evening",
            "scene": "normal",
        },
        {
            "name": "落地首日-乌鲁木齐推荐",
            "key": "urumqi_day1_recommendations",
            "channel": "wechat_work_group",
            "notification_type": "daily_reminder",
            "stage": "in_trip",
            "time_slot": "afternoon",
            "scene": "normal",
        },
        {
            "name": "晨间提示-春季",
            "key": "morning_spring",
            "channel": "sms",
            "notification_type": "daily_reminder",
            "stage": "in_trip",
            "time_slot": "morning",
            "scene": "normal",
        },
        {
            "name": "晨间提示-夏季",
            "key": "morning_summer",
            "channel": "sms",
            "notification_type": "daily_reminder",
            "stage": "in_trip",
            "time_slot": "morning",
            "scene": "normal",
        },
        {
            "name": "晨间提示-秋季",
            "key": "morning_autumn",
            "channel": "sms",
            "notification_type": "daily_reminder",
            "stage": "in_trip",
            "time_slot": "morning",
            "scene": "normal",
        },
        {
            "name": "晨间提示-冬季",
            "key": "morning_winter",
            "channel": "sms",
            "notification_type": "daily_reminder",
            "stage": "in_trip",
            "time_slot": "morning",
            "scene": "normal",
        },
        {
            "name": "午间提示-春季",
            "key": "noon_spring",
            "channel": "wechat_work_group",
            "notification_type": "daily_reminder",
            "stage": "in_trip",
            "time_slot": "afternoon",
            "scene": "normal",
        },
        {
            "name": "午间提示-夏季",
            "key": "noon_summer",
            "channel": "wechat_work_group",
            "notification_type": "daily_reminder",
            "stage": "in_trip",
            "time_slot": "afternoon",
            "scene": "normal",
        },
        {
            "name": "午间提示-秋季",
            "key": "noon_autumn",
            "channel": "wechat_work_group",
            "notification_type": "daily_reminder",
            "stage": "in_trip",
            "time_slot": "afternoon",
            "scene": "normal",
        },
        {
            "name": "午间提示-冬季",
            "key": "noon_winter",
            "channel": "wechat_work_group",
            "notification_type": "daily_reminder",
            "stage": "in_trip",
            "time_slot": "afternoon",
            "scene": "normal",
        },
        {
            "name": "场景提示-雨天",
            "key": "noon_rainy",
            "channel": "wechat_work_group",
            "notification_type": "risk_alert",
            "stage": "in_trip",
            "time_slot": "afternoon",
            "scene": "weather_alert",
        },
        {
            "name": "场景提示-骑马",
            "key": "horse_riding_notice",
            "channel": "wechat_work_group",
            "notification_type": "risk_alert",
            "stage": "in_trip",
            "time_slot": "afternoon",
            "scene": "weather_alert",
        },
        {
            "name": "场景提示-滑雪日",
            "key": "ski_day_notice",
            "channel": "wechat_work_group",
            "notification_type": "risk_alert",
            "stage": "in_trip",
            "time_slot": "afternoon",
            "scene": "weather_alert",
        },
        {
            "name": "晚间播报-次日行程",
            "key": "evening_next_day_preview",
            "channel": "wechat_work_group",
            "notification_type": "daily_reminder",
            "stage": "in_trip",
            "time_slot": "evening",
            "scene": "normal",
        },
        {
            "name": "行中协同-问题协调",
            "key": "issue_coordination_notice",
            "channel": "wechat_work_group",
            "notification_type": "risk_alert",
            "stage": "in_trip",
            "time_slot": "evening",
            "scene": "weather_alert",
        },
        {
            "name": "下团调研-满意度回访",
            "key": "post_trip_survey_notice",
            "channel": "sms",
            "notification_type": "satisfaction",
            "stage": "post_trip",
            "time_slot": "evening",
            "scene": "normal",
        },
        {
            "name": "下团欢送词",
            "key": "farewell_message",
            "channel": "wechat_work_group",
            "notification_type": "farewell",
            "stage": "post_trip",
            "time_slot": "evening",
            "scene": "normal",
        },
        {
            "name": "解散群文案",
            "key": "group_close_message",
            "channel": "wechat_work_group",
            "notification_type": "farewell",
            "stage": "post_trip",
            "time_slot": "evening",
            "scene": "normal",
        },
    ]

    for spec in template_specs:
        content = MESSAGE_TEMPLATES.get(spec["key"])
        if not content:
            continue
        template_service.create_notification_template(
            tenant_id=tenant_id,
            name=spec["name"],
            content=content,
            channel=spec["channel"],
            notification_type=spec["notification_type"],
            is_active=True,
            project_id=spec.get("project_id", ""),
            stage=spec.get("stage", ""),
            time_slot=spec.get("time_slot", ""),
            scene=spec.get("scene", ""),
            sms_sign_name=spec.get("sms_sign_name", ""),
            provider_template_code=spec.get("provider_template_code", ""),
        )


def _build_context(store: JsonFileStore | None = None) -> AppContext:
    persistence = store or JsonFileStore()
    trip_repository = TripRepository(store=persistence)
    project_notification_config_repository = ProjectNotificationConfigRepository(store=persistence)
    template_service = TemplateService(store=persistence)
    _seed_default_trips(trip_repository)
    _seed_concierge_templates(template_service, tenant_id="tenant-a")
    template_service.ensure_default_template(tenant_id="tenant-a")
    preference_service = UserPreferenceService(store=persistence)
    notification_attempt_repository = NotificationAttemptRepository(store=persistence)
    notification_rule_repository = NotificationRuleRepository(store=persistence)
    _seed_default_notification_rules(
        notification_rule_repository,
        template_id=template_service.ensure_default_template(tenant_id="tenant-a").id,
        tenant_id="tenant-a",
    )
    notification_service = NotificationService(
        idempotency_store=IdempotencyStore(store=persistence),
        attempt_repository=notification_attempt_repository,
    )
    async_dispatch_service = AsyncDispatchService(notification_service=notification_service)
    audit_service = AuditService(repository=AuditLogRepository(store=persistence))
    analytics_service = AnalyticsService(
        repository=AnalyticsRepository(store=persistence),
        attempt_repository=notification_attempt_repository,
        trip_repository=trip_repository,
    )
    auth_service = AuthService()
    weather_provider = WeatherProvider()
    return AppContext(
        store=persistence,
        auth_service=auth_service,
        trip_repository=trip_repository,
        project_notification_config_repository=project_notification_config_repository,
        template_service=template_service,
        preference_service=preference_service,
        notification_attempt_repository=notification_attempt_repository,
        notification_rule_repository=notification_rule_repository,
        notification_service=notification_service,
        async_dispatch_service=async_dispatch_service,
        audit_service=audit_service,
        analytics_service=analytics_service,
        weather_provider=weather_provider,
        notification_tasks={},
    )


def create_app() -> FastAPI:
    _patch_starlette_router_compat()

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        ctx = app.state.ctx
        scheduler = init_scheduler(ctx)
        scheduler.start()
        yield
        scheduler.stop()

    fastapi_app = FastAPI(
        title="Travel Notification API",
        version="0.2.0",
        lifespan=lifespan,
    )
    cors_origins = [
        origin.strip()
        for origin in os.getenv("TRAVEL_NOTIFICATION_CORS_ORIGINS", "").split(",")
        if origin.strip()
    ]
    if cors_origins:
        fastapi_app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
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

    def _current_tenant_id(user: dict[str, str]) -> str:
        tenant_id = str(user.get("tenant_id") or "").strip()
        if not tenant_id:
            raise HTTPException(status_code=403, detail="Tenant context missing")
        return tenant_id

    def _build_emergency_weather_service(ctx: AppContext) -> EmergencyWeatherService:
        return EmergencyWeatherService(
            trip_repository=ctx.trip_repository,
            project_notification_config_repository=ctx.project_notification_config_repository,
            weather_provider=ctx.weather_provider,
            risk_alert_service=RiskAlertService(),
            template_service=ctx.template_service,
            notification_service=ctx.notification_service,
        )

    def _build_notification_agent_service() -> NotificationAgentService:
        return NotificationAgentService()

    def _to_iso_date(value: Any) -> date | None:
        raw = str(value or "").strip()
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw).date()
        except ValueError:
            return None

    def _resolve_trip_for_group(
        ctx: AppContext, *, tenant_id: str, group_id: str, target_date: str
    ) -> dict[str, Any] | None:
        matched = [
            trip
            for trip in ctx.trip_repository.list()
            if str(trip.get("tenant_id") or "") == tenant_id
            and str(trip.get("team_id") or trip.get("team") or "") == group_id
        ]
        if not matched:
            return None

        target = _to_iso_date(target_date)
        if target is not None:
            for trip in matched:
                start = _to_iso_date(trip.get("start_date"))
                end = _to_iso_date(trip.get("end_date"))
                if start is not None and end is not None and start <= target <= end:
                    return trip

        matched_sorted = sorted(
            matched,
            key=lambda item: _to_iso_date(item.get("start_date")) or date.min,
            reverse=True,
        )
        return matched_sorted[0]

    def _resolve_daily_itinerary_context(trip: dict[str, Any], target_date: str) -> dict[str, Any]:
        itinerary = trip.get("itinerary")
        if not isinstance(itinerary, list):
            itinerary = []
        selected = next(
            (
                item
                for item in itinerary
                if isinstance(item, dict) and str(item.get("date") or "") == target_date
            ),
            {},
        )
        route_text = str(
            selected.get("route")
            or selected.get("title")
            or trip.get("destination")
            or trip.get("team")
            or ""
        )
        hotel = str(selected.get("hotel") or selected.get("hotel_name") or "")
        special_tags = selected.get("special_tags")
        if not isinstance(special_tags, list):
            special_tags = []
        return {
            "route_text": route_text,
            "hotel": hotel,
            "special_tags": [str(item) for item in special_tags if str(item).strip()],
        }

    def _require_permission_or_403(user: dict[str, str], permission: str) -> None:
        try:
            require_permission(user, permission)
        except PermissionDenied as exc:
            raise HTTPException(status_code=403, detail=exc.message) from exc

    def assert_trip_access(user: dict[str, str], trip: dict[str, Any]) -> None:
        try:
            assert_tenant_scope(user, str(trip.get("tenant_id") or ""))
            require_permission(user, "trip:read")
        except PermissionDenied as exc:
            raise HTTPException(status_code=403, detail=exc.message) from exc
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
        queue_health = ctx.async_dispatch_service.health_snapshot()
        return _ok(
            {
                "status": "ok",
                "time": datetime.now(tz=UTC).isoformat(),
                **queue_health,
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
        try:
            token = ctx.auth_service.login(payload.username, payload.password)
            if token is None:
                raise HTTPException(status_code=401, detail="Invalid credentials")
            return _ok(token)
        except HTTPException:
            raise
        except Exception as e:
            import traceback

            error_detail = traceback.format_exc()
            return JSONResponse(
                status_code=500, content={"code": 500, "error": str(e), "detail": error_detail}
            )

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
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "template:read")
        tenant_id = _current_tenant_id(user)
        items = [
            _serialize_template(item)
            for item in ctx.template_service.list_notification_templates(tenant_id=tenant_id)
        ]
        return _ok({"total": len(items), "items": items})

    @fastapi_app.get("/api/templates/{template_id}")
    def get_template(
        template_id: str,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        template = ctx.template_service.get_notification_template(
            template_id, tenant_id=_current_tenant_id(user)
        )
        if template is None:
            raise HTTPException(status_code=404, detail="Template not found")
        return _ok(_serialize_template(template))

    @fastapi_app.post("/api/templates", status_code=201)
    def create_template(
        payload: TemplateCreateRequest,
        user: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "template:write")
        template = ctx.template_service.create_notification_template(
            tenant_id=_current_tenant_id(user),
            name=payload.name,
            content=payload.content,
            channel=_parse_channel(payload.channel).value,
            notification_type=payload.notification_type,
            is_active=payload.is_active,
            project_id=payload.project_id,
            stage=payload.stage,
            time_slot=payload.time_slot,
            scene=payload.scene,
            sms_sign_name=payload.sms_sign_name,
            provider_template_code=payload.provider_template_code,
        )
        return _ok(_serialize_template(template))

    @fastapi_app.put("/api/templates/{template_id}")
    def update_template(
        template_id: str,
        payload: TemplateUpdateRequest,
        user: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "template:write")
        tenant_id = _current_tenant_id(user)
        existing = ctx.template_service.get_notification_template(template_id, tenant_id=tenant_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Template not found")
        template = ctx.template_service.update_notification_template(
            template_id,
            name=payload.name,
            content=payload.content,
            channel=None if payload.channel is None else _parse_channel(payload.channel).value,
            notification_type=payload.notification_type,
            is_active=payload.is_active,
            project_id=payload.project_id,
            stage=payload.stage,
            time_slot=payload.time_slot,
            scene=payload.scene,
            sms_sign_name=payload.sms_sign_name,
            provider_template_code=payload.provider_template_code,
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
        user: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "template:write")
        template = ctx.template_service.get_notification_template(
            template_id, tenant_id=_current_tenant_id(user)
        )
        if template is None:
            raise HTTPException(status_code=404, detail="Template not found")
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

    @fastapi_app.post("/api/notifications/templates/agent-drafts")
    def generate_agent_notification_drafts(
        payload: AgentNotificationDraftRequest,
        user: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "template:write")
        tenant_id = _current_tenant_id(user)
        channel = _parse_channel(payload.channel).value
        agent = _build_notification_agent_service()
        result = agent.generate_daily_drafts(
            route=payload.route,
            travel_stage=payload.travel_stage,
            time_node=payload.time_node,
            core_work=payload.core_work,
            action_detail=payload.action_detail,
        )
        drafts = result["drafts"]
        created_template_ids: list[str] = []
        if payload.save_as_templates:
            for item in drafts:
                template = ctx.template_service.create_notification_template(
                    tenant_id=tenant_id,
                    name=f"{payload.template_prefix}-{result['context']['time_node']}-{item['title']}",
                    content=item["content"],
                    channel=channel,
                    notification_type=payload.notification_type,
                    is_active=True,
                    project_id=payload.project_id,
                    stage=payload.travel_stage,
                    time_slot=item["time_slot"],
                    scene="agent_generated",
                )
                created_template_ids.append(template.id)
        ctx.audit_service.record(
            operator_id=user["id"],
            action="template_agent_drafts_generated",
            target=payload.project_id or payload.route,
            detail={
                "draft_count": len(drafts),
                "saved": payload.save_as_templates,
                "template_ids": created_template_ids,
            },
        )
        return _ok(
            {
                **result,
                "saved_as_templates": payload.save_as_templates,
                "created_template_ids": created_template_ids,
            }
        )

    @fastapi_app.get("/api/project-configs")
    def list_project_configs(
        user: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        tenant_id = _current_tenant_id(user)
        items = [
            _serialize_project_notification_config(item)
            for item in ctx.project_notification_config_repository.list(tenant_id=tenant_id)
        ]
        return _ok({"total": len(items), "items": items})

    @fastapi_app.get("/api/project-configs/{project_id}")
    def get_project_config(
        project_id: str,
        user: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        config = ctx.project_notification_config_repository.get(
            project_id,
            tenant_id=_current_tenant_id(user),
        )
        if config is None:
            raise HTTPException(status_code=404, detail="Project config not found")
        return _ok(_serialize_project_notification_config(config))

    @fastapi_app.get("/api/trips/{trip_id}/notification-config")
    def get_trip_notification_config(
        trip_id: str,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        trip = ctx.trip_repository.get(trip_id)
        if trip is None:
            raise HTTPException(status_code=404, detail="Trip not found")
        assert_trip_access(user, trip)
        project_id = str(trip.get("team_id") or trip.get("team") or trip_id)
        config = ctx.project_notification_config_repository.get(
            project_id,
            tenant_id=_current_tenant_id(user),
        )
        if config is None:
            config = {
                "tenant_id": _current_tenant_id(user),
                "project_id": project_id,
                "project_name": "",
                "weather_enabled": True,
                "qweather_credential_id": "",
                "qweather_location_id": "",
                "qweather_lat": "",
                "qweather_lon": "",
                "weather_alert_thresholds": {},
                "sms_provider": "aliyun",
                "sms_sign_name": "",
                "sms_template_code_normal": "",
                "sms_template_code_weather_alert": "",
                "manual_takeover_target": "",
            }
        return _ok(_serialize_project_notification_config(config))

    @fastapi_app.put("/api/project-configs/{project_id}")
    def upsert_project_config(
        project_id: str,
        payload: ProjectNotificationConfigUpsertRequest,
        user: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        config = ctx.project_notification_config_repository.upsert(
            {
                "tenant_id": _current_tenant_id(user),
                "project_id": project_id,
                "project_name": payload.project_name,
                "weather_enabled": payload.weather_enabled,
                "qweather_credential_id": payload.qweather_credential_id,
                "qweather_location_id": payload.qweather_location_id,
                "qweather_lat": payload.qweather_lat,
                "qweather_lon": payload.qweather_lon,
                "weather_alert_thresholds": payload.weather_alert_thresholds,
                "sms_provider": payload.sms_provider,
                "sms_sign_name": payload.sms_sign_name,
                "sms_template_code_normal": payload.sms_template_code_normal,
                "sms_template_code_weather_alert": payload.sms_template_code_weather_alert,
                "manual_takeover_target": payload.manual_takeover_target,
            }
        )
        ctx.audit_service.record(
            operator_id=user["id"],
            action="project_config_upserted",
            target=project_id,
            detail={"tenant_id": _current_tenant_id(user)},
        )
        return _ok(_serialize_project_notification_config(config))

    @fastapi_app.put("/api/trips/{trip_id}/notification-config")
    def upsert_trip_notification_config(
        trip_id: str,
        payload: ProjectNotificationConfigUpsertRequest,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        trip = ctx.trip_repository.get(trip_id)
        if trip is None:
            raise HTTPException(status_code=404, detail="Trip not found")
        assert_trip_access(user, trip)
        _require_permission_or_403(user, "rule:write")
        project_id = str(trip.get("team_id") or trip.get("team") or trip_id)
        config = ctx.project_notification_config_repository.upsert(
            {
                "tenant_id": _current_tenant_id(user),
                "project_id": project_id,
                "project_name": payload.project_name,
                "weather_enabled": payload.weather_enabled,
                "qweather_credential_id": payload.qweather_credential_id,
                "qweather_location_id": payload.qweather_location_id,
                "qweather_lat": payload.qweather_lat,
                "qweather_lon": payload.qweather_lon,
                "weather_alert_thresholds": payload.weather_alert_thresholds,
                "sms_provider": payload.sms_provider,
                "sms_sign_name": payload.sms_sign_name,
                "sms_template_code_normal": payload.sms_template_code_normal,
                "sms_template_code_weather_alert": payload.sms_template_code_weather_alert,
                "manual_takeover_target": payload.manual_takeover_target,
            }
        )
        ctx.audit_service.record(
            operator_id=user["id"],
            action="trip_notification_config_upserted",
            target=trip_id,
            detail={"project_id": project_id, "tenant_id": _current_tenant_id(user)},
        )
        return _ok(_serialize_project_notification_config(config))

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
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "rule:read")
        try:
            tenant_id = _current_tenant_id(user)
            items = ctx.notification_rule_repository.list_rules(
                tenant_id=tenant_id,
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
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        rule = ctx.notification_rule_repository.get_rule(
            rule_id, tenant_id=_current_tenant_id(user)
        )
        if rule is None:
            raise HTTPException(status_code=404, detail="Rule not found")
        return _ok_with_message(rule, "rule found")

    @fastapi_app.post("/api/notifications/rules", status_code=201)
    def create_notification_rule(
        payload: NotificationRuleCreateRequest,
        user: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "rule:write")
        try:
            rule = ctx.notification_rule_repository.create_rule(
                {**payload.model_dump(), "tenant_id": _current_tenant_id(user)}
            )
        except RuleValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _ok_with_message(rule, "rule created")

    @fastapi_app.put("/api/notifications/rules/{rule_id}")
    def update_notification_rule(
        rule_id: str,
        payload: NotificationRuleUpdateRequest,
        user: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "rule:write")
        try:
            rule = ctx.notification_rule_repository.update_rule(
                rule_id,
                payload.model_dump(exclude_none=True),
                tenant_id=_current_tenant_id(user),
            )
        except RuleValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if rule is None:
            raise HTTPException(status_code=404, detail="Rule not found")
        return _ok_with_message(rule, "rule updated")

    @fastapi_app.delete("/api/notifications/rules/{rule_id}")
    def delete_notification_rule(
        rule_id: str,
        user: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "rule:write")
        deleted = ctx.notification_rule_repository.delete_rule(
            rule_id, tenant_id=_current_tenant_id(user)
        )
        if not deleted:
            raise HTTPException(status_code=404, detail="Rule not found")
        return _ok_with_message({"deleted": True, "id": rule_id}, "rule deleted")

    def _record_rule_audit(
        user: dict[str, str], ctx: AppContext, action: str, rule: dict[str, Any]
    ) -> None:
        ctx.audit_service.record(
            operator_id=user["id"],
            action=action,
            target=str(rule.get("id") or ""),
            detail={"status": rule.get("status"), "tenant_id": rule.get("tenant_id")},
        )

    @fastapi_app.post("/api/notifications/rules/{rule_id}/submit")
    def submit_notification_rule(
        rule_id: str,
        user: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "rule:write")
        try:
            rule = ctx.notification_rule_repository.submit_rule(
                rule_id, tenant_id=_current_tenant_id(user), operator_id=user["id"]
            )
        except RuleValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if rule is None:
            raise HTTPException(status_code=404, detail="Rule not found")
        _record_rule_audit(user, ctx, "rule_submit", rule)
        return _ok_with_message(rule, "rule submitted")

    @fastapi_app.post("/api/notifications/rules/{rule_id}/approve")
    def approve_notification_rule(
        rule_id: str,
        payload: RuleReviewRequest,
        user: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "rule:approve")
        try:
            rule = ctx.notification_rule_repository.approve_rule(
                rule_id, tenant_id=_current_tenant_id(user), operator_id=user["id"]
            )
        except RuleValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if rule is None:
            raise HTTPException(status_code=404, detail="Rule not found")
        _record_rule_audit(user, ctx, "rule_approve", rule)
        if payload.comment:
            ctx.audit_service.record(
                operator_id=user["id"],
                action="rule_approve_comment",
                target=rule_id,
                detail={"comment": payload.comment[:200]},
            )
        return _ok_with_message(rule, "rule approved")

    @fastapi_app.post("/api/notifications/rules/{rule_id}/reject")
    def reject_notification_rule(
        rule_id: str,
        payload: RuleRejectRequest,
        user: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "rule:approve")
        try:
            rule = ctx.notification_rule_repository.reject_rule(
                rule_id,
                tenant_id=_current_tenant_id(user),
                operator_id=user["id"],
                reason=payload.reason.strip(),
            )
        except RuleValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if rule is None:
            raise HTTPException(status_code=404, detail="Rule not found")
        _record_rule_audit(user, ctx, "rule_reject", rule)
        return _ok_with_message(rule, "rule rejected")

    @fastapi_app.post("/api/notifications/rules/{rule_id}/publish")
    def publish_notification_rule(
        rule_id: str,
        payload: RuleReviewRequest,
        user: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "rule:approve")
        try:
            rule = ctx.notification_rule_repository.publish_rule(
                rule_id, tenant_id=_current_tenant_id(user), operator_id=user["id"]
            )
        except RuleValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if rule is None:
            raise HTTPException(status_code=404, detail="Rule not found")
        _record_rule_audit(user, ctx, "rule_publish", rule)
        if payload.comment:
            ctx.audit_service.record(
                operator_id=user["id"],
                action="rule_publish_comment",
                target=rule_id,
                detail={"comment": payload.comment[:200]},
            )
        return _ok_with_message(rule, "rule published")

    @fastapi_app.post("/api/notifications/rules/simulate")
    def simulate_notification_rule(
        payload: RuleSimulationRequest,
        user: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "rule:read")
        try:
            result = ctx.notification_rule_repository.simulate(
                tenant_id=_current_tenant_id(user),
                stage=payload.stage,
                time_slot=payload.time_slot,
                scene=payload.scene,
                context=payload.context,
            )
        except RuleValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _ok_with_message(result, "rule simulation completed")

    @fastapi_app.get("/api/workbench/today/overview")
    def get_workbench_today_overview(
        date: str | None = None,
        owner_scope: str = "mine",
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "trip:read")
        tenant_id = _current_tenant_id(user)
        effective_scope = "all" if user.get("role") == "admin" and owner_scope == "all" else "mine"
        tasks = _ensure_workbench_tasks(ctx, tenant_id=tenant_id, owner_scope=effective_scope)
        if effective_scope == "mine":
            tasks = [item for item in tasks if item.get("owner_id") == user.get("id")]
        normalized = [{**item, "status": _task_status_for_due(item)} for item in tasks]
        pending = [item for item in normalized if item.get("status") not in {"done"}]
        overdue = [item for item in normalized if item.get("status") == "overdue"]
        risky = [item for item in normalized if str(item.get("risk_level")) in {"high", "critical"}]
        takeovers = [
            item for item in normalized if str(item.get("status")) == "handover_in_progress"
        ]
        return _ok(
            {
                "date": date or datetime.now(tz=UTC).date().isoformat(),
                "timezone": "UTC",
                "pending_tasks": len(pending),
                "overdue_tasks": len(overdue),
                "risky_trips": len({str(item.get("trip_id")) for item in risky}),
                "pending_takeovers": len(takeovers),
            }
        )

    @fastapi_app.get("/api/workbench/today/action-items")
    def get_workbench_action_items(
        limit: int = 20,
        owner_scope: str = "mine",
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "trip:read")
        tenant_id = _current_tenant_id(user)
        effective_scope = "all" if user.get("role") == "admin" and owner_scope == "all" else "mine"
        tasks = _ensure_workbench_tasks(ctx, tenant_id=tenant_id, owner_scope=effective_scope)
        if effective_scope == "mine":
            tasks = [item for item in tasks if item.get("owner_id") == user.get("id")]
        items = [{**item, "status": _task_status_for_due(item)} for item in tasks]
        items_sorted = sorted(
            items,
            key=lambda item: (str(item.get("status") != "overdue"), str(item.get("due_at") or "")),
        )
        return _ok({"items": items_sorted[: max(limit, 0)]})

    @fastapi_app.get("/api/trips/execution")
    def list_trip_execution(
        owner_scope: str = "mine",
        stage: str | None = None,
        risk_level: str | None = None,
        date: str | None = None,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "trip:read")
        tenant_id = _current_tenant_id(user)
        effective_scope = "all" if user.get("role") == "admin" and owner_scope == "all" else "mine"
        tasks = _ensure_workbench_tasks(ctx, tenant_id=tenant_id, owner_scope=effective_scope)
        if effective_scope == "mine":
            tasks = [item for item in tasks if item.get("owner_id") == user.get("id")]
        if stage:
            tasks = [item for item in tasks if str(item.get("stage")) == stage]
        if risk_level:
            tasks = [item for item in tasks if str(item.get("risk_level")) == risk_level]
        grouped: dict[str, list[dict[str, Any]]] = {}
        for task in tasks:
            grouped.setdefault(str(task.get("trip_id") or ""), []).append(task)
        trips = {
            str(item.get("id") or ""): item
            for item in ctx.trip_repository.list()
            if str(item.get("tenant_id") or "") == tenant_id
        }
        rows: list[dict[str, Any]] = []
        now = datetime.now(tz=UTC)
        for trip_id, trip_tasks in grouped.items():
            trip = trips.get(trip_id)
            if trip is None:
                continue
            statuses = [_task_status_for_due(item) for item in trip_tasks]
            todo_count = len([status for status in statuses if status != "done"])
            overdue_minutes = 0
            next_due_candidates: list[str] = []
            for item in trip_tasks:
                due_at = str(item.get("due_at") or "")
                if due_at:
                    next_due_candidates.append(due_at)
                if _task_status_for_due(item) == "overdue":
                    try:
                        due = datetime.fromisoformat(due_at.replace("Z", "+00:00"))
                    except ValueError:
                        continue
                    overdue_minutes = max(overdue_minutes, int((now - due).total_seconds() // 60))
            dispatch_status = "pending"
            if any(status == "handover_in_progress" for status in statuses):
                dispatch_status = "manual_intervention"
            elif todo_count == 0:
                dispatch_status = "sent"
            rows.append(
                {
                    "trip_id": trip_id,
                    "team_id": str(trip.get("team_id") or trip.get("team") or ""),
                    "trip_name": str(trip.get("destination") or trip_id),
                    "current_stage": str(trip_tasks[0].get("stage") or "unknown"),
                    "todo_count": todo_count,
                    "total_count": len(trip_tasks),
                    "next_node_due_at": min(next_due_candidates) if next_due_candidates else "",
                    "risk_level": max(
                        (str(item.get("risk_level") or "low") for item in trip_tasks),
                        key=lambda level: {"low": 1, "medium": 2, "high": 3, "critical": 4}.get(
                            level, 0
                        ),
                    ),
                    "dispatch_status": dispatch_status,
                    "owner_name": str(trip_tasks[0].get("owner_name") or ""),
                    "overdue_minutes": overdue_minutes,
                    "date": date or datetime.now(tz=UTC).date().isoformat(),
                }
            )
        rows_sorted = sorted(
            rows,
            key=lambda item: (
                -int(item.get("overdue_minutes") or 0),
                str(item.get("risk_level") not in {"critical", "high"}),
                str(item.get("next_node_due_at") or ""),
            ),
        )
        return _ok({"items": rows_sorted})

    @fastapi_app.get("/api/trips/{trip_id}/execution")
    def get_trip_execution_detail(
        trip_id: str,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "trip:read")
        trip = ctx.trip_repository.get(trip_id)
        if trip is None:
            raise HTTPException(status_code=404, detail="Trip not found")
        assert_trip_access(user, trip)
        tenant_id = _current_tenant_id(user)
        tasks = _ensure_workbench_tasks(ctx, tenant_id=tenant_id)
        trip_tasks = [item for item in tasks if str(item.get("trip_id")) == trip_id]
        normalized = [{**item, "status": _task_status_for_due(item)} for item in trip_tasks]
        today_total = len(normalized)
        today_done = len([item for item in normalized if item.get("status") == "done"])
        risk = "low"
        if any(str(item.get("risk_level")) == "high" for item in normalized):
            risk = "high"
        elif any(str(item.get("risk_level")) == "medium" for item in normalized):
            risk = "medium"
        return _ok(
            {
                "trip_id": trip_id,
                "team_id": str(trip.get("team_id") or trip.get("team") or ""),
                "trip_name": str(trip.get("destination") or trip_id),
                "current_stage": str(normalized[0].get("stage") if normalized else "unknown"),
                "today_total": today_total,
                "today_done": today_done,
                "risk_level": risk,
                "next_dispatch_at": (
                    min(
                        [str(item.get("due_at") or "") for item in normalized if item.get("due_at")]
                    )
                    if normalized
                    else ""
                ),
                "tasks": [
                    {
                        "task_id": item.get("id"),
                        "title": item.get("title"),
                        "stage": item.get("stage"),
                        "node_key": item.get("node_key"),
                        "due_at": item.get("due_at"),
                        "status": item.get("status"),
                        "owner_role": item.get("owner_role"),
                        "owner_name": item.get("owner_name"),
                        "evidence_required": item.get("priority") == "p0",
                        "dispatch_id": item.get("dispatch_id") or "",
                    }
                    for item in normalized
                ],
            }
        )

    @fastapi_app.get("/api/trips")
    def list_trips(
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "trip:read")
        tenant_id = _current_tenant_id(user)
        items = [item for item in ctx.trip_repository.list() if item.get("tenant_id") == tenant_id]
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
            "tenant_id": _current_tenant_id(user),
            "created_at": now,
            "updated_at": now,
        }
        ctx.trip_repository.create(trip)

        template = next(
            (
                item
                for item in ctx.template_service.list_notification_templates(
                    tenant_id=_current_tenant_id(user)
                )
                if item.is_active
            ),
            ctx.template_service.ensure_default_template(tenant_id=_current_tenant_id(user)),
        )
        rendered = ctx.template_service.render_notification(
            template,
            {
                "customer_name": user.get("username", user["id"]),
                "destination": payload.destination,
            },
        )
        task = NotificationTask(
            tenant_id=_current_tenant_id(user),
            team_id=team_id,
            trip_id=trip_id,
            customer_id=user["id"],
            rendered_content=rendered,
            idempotency_key=f"{trip_id}:created",
            primary_channel=Channel.SMS,
            fallback_channel=Channel.WECHAT_WORK_GROUP,
        )
        ctx.notification_tasks[task.id] = task
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
        _require_permission_or_403(user, "trip:write")
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
            workbook_rows: dict[str, list[dict[str, str]]] = {}
        elif filename.endswith(".xlsx"):
            workbook_rows = _read_xlsx_workbook_rows(raw)
            parsed_rows = _read_xlsx_rows(raw)
        else:
            raise HTTPException(status_code=400, detail="Only .csv and .xlsx files are supported")

        structured_trip = _build_structured_trip_import(workbook_rows) if workbook_rows else None
        if structured_trip is not None:
            trip_payload = TripCreateRequest(
                destination=structured_trip["destination"],
                team_id=structured_trip["team_id"],
                start_date=structured_trip["start_date"],
                end_date=structured_trip["end_date"],
                participants=structured_trip["participants"],
                status="计划中",
            )
            created = create_trip_record(payload=trip_payload, user=user, ctx=ctx)
            trip = created["trip"]
            patch: dict[str, Any] = {
                "itinerary": structured_trip["itinerary"],
                "guests": structured_trip["guests"],
                "participants": max(
                    structured_trip["participants"], len(structured_trip["guests"])
                ),
            }
            if structured_trip["guests"]:
                patch["leader_name"] = structured_trip["guests"][0].get("name", "")
                patch["contact_phone"] = structured_trip["guests"][0].get("phone", "")
            updated_trip = ctx.trip_repository.update(trip["id"], patch)
            return _ok(
                {
                    "created_count": 1,
                    "skipped_count": 0,
                    "items": [_serialize_trip(updated_trip or trip)],
                }
            )

        created_items: list[dict[str, Any]] = []
        skipped = 0
        for row in parsed_rows:
            destination = _extract_import_field(row, ["destination", "目的地", "行程名称"])
            team_id = _extract_import_field(row, ["team_id", "team", "teamid", "团队ID", "团队"])
            start_date = _extract_import_field(
                row, ["start_date", "startdate", "开始日期", "开始时间"]
            )
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

    @fastapi_app.get("/api/trips/{trip_id}")
    def get_trip(
        trip_id: str,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        trip = ctx.trip_repository.get(trip_id)
        if trip is None:
            raise HTTPException(status_code=404, detail="Trip not found")
        assert_trip_access(user, trip)
        return _ok(_serialize_trip(trip))

    @fastapi_app.get("/api/trips/{trip_id}/import-snapshot")
    def get_trip_import_snapshot(
        trip_id: str,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        trip = ctx.trip_repository.get(trip_id)
        if trip is None:
            raise HTTPException(status_code=404, detail="Trip not found")
        assert_trip_access(user, trip)
        return _ok(_build_trip_import_snapshot(trip))

    @fastapi_app.put("/api/trips/{trip_id}/import-validation")
    def apply_trip_import_validation(
        trip_id: str,
        payload: TripImportValidationApplyRequest,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "trip:write")
        trip = ctx.trip_repository.get(trip_id)
        if trip is None:
            raise HTTPException(status_code=404, detail="Trip not found")
        assert_trip_access(user, trip)
        fields = payload.fields
        patched: dict[str, Any] = dict(trip)
        leader_phone = str(fields.get("leader_phone", "")).strip()
        leader_name = str(fields.get("leader_name", "")).strip()
        if leader_phone:
            patched["contact_phone"] = leader_phone
        if leader_name:
            patched["leader_name"] = leader_name
        patched["updated_at"] = datetime.now(UTC).isoformat()
        saved = ctx.trip_repository.update(trip_id, patched)
        return _ok(
            {
                "trip": _serialize_trip(saved),
                "snapshot": _build_trip_import_snapshot(saved),
            }
        )

    @fastapi_app.get("/api/trips/{trip_id}/schedule")
    def get_trip_schedule(
        trip_id: str,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        trip = ctx.trip_repository.get(trip_id)
        if trip is None:
            raise HTTPException(status_code=404, detail="Trip not found")
        assert_trip_access(user, trip)
        tenant_id = _current_tenant_id(user)
        team_id = str(trip.get("team_id") or trip.get("team") or "")
        notification_items = _query_notification_items(
            repository=ctx.notification_attempt_repository,
            limit=5,
            trip_id=trip_id,
            team_id=team_id or None,
            customer_id=None,
            tenant_id=tenant_id,
        )
        return _ok(_serialize_trip_schedule(trip, notification_items))

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
        if "itinerary" in patch and patch["itinerary"] is None:
            patch["itinerary"] = []
        if "guests" in patch and patch["guests"] is None:
            patch["guests"] = []
        if "guests" in patch and isinstance(patch["guests"], list):
            patch["participants"] = len(patch["guests"])
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

    @fastapi_app.post("/api/notifications/generate-daily")
    def generate_daily_notifications(
        payload: DailyNotificationGenerateRequest,
        user: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "notification:write")
        tenant_id = _current_tenant_id(user)
        trip = _resolve_trip_for_group(
            ctx,
            tenant_id=tenant_id,
            group_id=payload.group_id,
            target_date=payload.date,
        )
        if trip is None:
            raise HTTPException(status_code=404, detail="Trip group not found")
        itinerary_ctx = _resolve_daily_itinerary_context(trip, payload.date)
        service = _build_notification_agent_service()
        generated = service.generate_daily_messages(
            group_id=payload.group_id,
            group_name=str(trip.get("team") or trip.get("team_id") or payload.group_id),
            travel_date=payload.date,
            start_date=str(trip.get("start_date") or payload.date),
            end_date=str(trip.get("end_date") or payload.date),
            route_text=itinerary_ctx["route_text"],
            hotel=itinerary_ctx["hotel"],
            weather=payload.weather,
            core_work=payload.core_work,
            special_tags=itinerary_ctx["special_tags"],
        )
        created_template_ids: list[str] = []
        if payload.save_as_templates:
            channel = _parse_channel(payload.channel).value
            for item in generated["messages"]:
                template = ctx.template_service.create_notification_template(
                    tenant_id=tenant_id,
                    name=f"Agent日播-{payload.group_id}-{item['period']}",
                    content=item["message"],
                    channel=channel,
                    notification_type="daily_reminder",
                    is_active=True,
                    project_id=payload.project_id,
                    stage=generated["stage"],
                    time_slot=item["period"],
                    scene="agent_generated_daily",
                )
                created_template_ids.append(template.id)
        generated["created_template_ids"] = created_template_ids
        ctx.audit_service.record(
            operator_id=user["id"],
            action="notification_daily_generated",
            target=payload.group_id,
            detail={
                "date": payload.date,
                "stage": generated["stage"],
                "time_node": generated["time_node"],
                "saved_templates": bool(created_template_ids),
            },
        )
        return _ok(generated)

    @fastapi_app.post("/api/notifications/dispatch/preview")
    def preview_notification_dispatch(
        payload: DispatchPreviewRequest,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "notification:read")
        trip = ctx.trip_repository.get(payload.trip_id)
        if trip is None:
            raise HTTPException(status_code=404, detail="Trip not found")
        assert_trip_access(user, trip)
        tenant_id = _current_tenant_id(user)
        template = None
        if payload.template_id:
            template = ctx.template_service.get_notification_template(
                payload.template_id, tenant_id
            )
        if template is None:
            template = ctx.template_service.ensure_default_template(tenant_id=tenant_id)
        variables = {
            "customer_name": "全团游客",
            "destination": str(trip.get("destination") or ""),
        }
        try:
            content = ctx.template_service.render_notification(template, variables)
            variable_check = {"ok": True, "missing_fields": []}
        except ValueError as exc:
            content = template.content
            variable_check = {"ok": False, "missing_fields": _parse_missing_fields(exc)}
        return _ok(
            {
                "trip_id": payload.trip_id,
                "node_key": payload.node_key,
                "channel": _parse_channel(payload.channel).value,
                "template_id": template.id,
                "content": content,
                "variable_check": variable_check,
            }
        )

    @fastapi_app.post("/api/notifications/dispatch")
    def dispatch_notification_now(
        payload: DispatchNowRequest,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "notification:write")
        trip = ctx.trip_repository.get(payload.trip_id)
        if trip is None:
            raise HTTPException(status_code=404, detail="Trip not found")
        assert_trip_access(user, trip)
        tenant_id = _current_tenant_id(user)
        content = (payload.content or "").strip()
        template = None
        if not content:
            if payload.template_id:
                template = ctx.template_service.get_notification_template(
                    payload.template_id, tenant_id
                )
            if template is None:
                template = ctx.template_service.ensure_default_template(tenant_id=tenant_id)
            content = ctx.template_service.render_notification(
                template,
                {
                    "customer_name": "全团游客",
                    "destination": str(trip.get("destination") or ""),
                },
            )
        dispatch_task = NotificationTask(
            tenant_id=tenant_id,
            team_id=str(trip.get("team_id") or trip.get("team") or ""),
            trip_id=payload.trip_id,
            customer_id=user["id"],
            rendered_content=content,
            idempotency_key=f"workbench:{payload.trip_id}:{payload.node_key}:{uuid4().hex}",
            primary_channel=_parse_channel(payload.channel),
            fallback_channel=Channel.WECHAT_WORK_GROUP,
            provider_context={
                "customer_name": "全团游客",
                "trip_label": str(trip.get("destination") or payload.trip_id),
            },
        )
        ctx.notification_tasks[dispatch_task.id] = dispatch_task
        result = ctx.notification_service.dispatch(dispatch_task)
        dispatch_id = dispatch_task.attempts[-1].id if dispatch_task.attempts else dispatch_task.id

        tasks = _ensure_workbench_tasks(ctx, tenant_id=tenant_id)
        for item in tasks:
            if (
                str(item.get("trip_id")) == payload.trip_id
                and str(item.get("node_key")) == payload.node_key
            ):
                item["dispatch_id"] = dispatch_id
                item["updated_at"] = _now_iso()
                item["status"] = "done" if result.get("ok") else "handover_in_progress"
                break
        _save_workbench_tasks(ctx, tenant_id, tasks)
        return _ok(
            {
                "ok": bool(result.get("ok")),
                "status": "sent" if result.get("ok") else "manual_intervention",
                "message": "dispatch sent" if result.get("ok") else "dispatch failed",
                "task_id": dispatch_task.id,
                "dispatch_id": dispatch_id,
            }
        )

    @fastapi_app.post("/api/notifications/dispatch/{dispatch_id}/retry")
    def retry_dispatch(
        dispatch_id: str,
        payload: RetryDispatchRequest,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "notification:write")
        tenant_id = _current_tenant_id(user)
        history = ctx.notification_attempt_repository.list_history(limit=None)
        matched = next((item for item in history if item.get("attempt_id") == dispatch_id), None)
        if matched is None:
            raise HTTPException(status_code=404, detail="Dispatch not found")
        trip_id = str(matched.get("trip_id") or "")
        trip = ctx.trip_repository.get(trip_id)
        if trip is None:
            raise HTTPException(status_code=404, detail="Trip not found")
        assert_trip_access(user, trip)
        retry_task = NotificationTask(
            tenant_id=tenant_id,
            team_id=str(matched.get("team_id") or ""),
            trip_id=trip_id,
            customer_id=str(matched.get("customer_id") or user["id"]),
            rendered_content=str(matched.get("provider_message") or "重试通知"),
            idempotency_key=f"retry:{dispatch_id}:{uuid4().hex}",
            primary_channel=_parse_channel(str(matched.get("channel") or "sms")),
            fallback_channel=Channel.WECHAT_WORK_GROUP,
            provider_context={
                "customer_name": str(matched.get("customer_name") or "游客"),
                "trip_label": str(matched.get("trip_label") or trip_id),
            },
        )
        ctx.notification_tasks[retry_task.id] = retry_task
        ctx.notification_service.dispatch(retry_task)
        latest_dispatch_id = retry_task.attempts[-1].id if retry_task.attempts else retry_task.id
        return _ok(
            {
                "ok": True,
                "status": "retrying",
                "message": payload.reason or "dispatch retry accepted",
                "task_id": retry_task.id,
                "dispatch_id": latest_dispatch_id,
            }
        )

    @fastapi_app.post("/api/workbench/takeovers")
    def assign_workbench_takeover(
        payload: AssignTakeoverRequest,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "notification:write")
        tenant_id = _current_tenant_id(user)
        tasks = _ensure_workbench_tasks(ctx, tenant_id=tenant_id)
        target = next((item for item in tasks if item.get("id") == payload.task_id), None)
        if target is None:
            raise HTTPException(status_code=404, detail="Task not found")
        target["status"] = "handover_in_progress"
        target["assignee_user_id"] = payload.assignee_user_id
        target["assignee_name"] = payload.assignee_name or payload.assignee_user_id
        target["deadline_at"] = payload.deadline_at or ""
        target["note"] = payload.note or ""
        target["updated_at"] = _now_iso()
        _save_workbench_tasks(ctx, tenant_id, tasks)
        return _ok(
            {
                "ok": True,
                "status": "handover_in_progress",
                "message": "takeover assigned",
                "task_id": target.get("id"),
                "dispatch_id": target.get("dispatch_id") or "",
            }
        )

    @fastapi_app.post("/api/workbench/tasks/{task_id}/complete")
    def complete_workbench_task(
        task_id: str,
        payload: CompleteWorkbenchTaskRequest,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "notification:write")
        tenant_id = _current_tenant_id(user)
        tasks = _ensure_workbench_tasks(ctx, tenant_id=tenant_id)
        target = next((item for item in tasks if item.get("id") == task_id), None)
        if target is None:
            raise HTTPException(status_code=404, detail="Task not found")
        target["status"] = "done"
        target["result_note"] = payload.result_note or ""
        target["evidence_type"] = payload.evidence_type or "none"
        target["evidence_ref"] = payload.evidence_ref or ""
        target["updated_at"] = _now_iso()
        _save_workbench_tasks(ctx, tenant_id, tasks)
        return _ok(
            {
                "ok": True,
                "status": "done",
                "message": "task completed",
                "task_id": target.get("id"),
                "dispatch_id": target.get("dispatch_id") or "",
            }
        )

    @fastapi_app.post("/api/workbench/tasks/{task_id}/nudge")
    def nudge_workbench_task(
        task_id: str,
        payload: NudgeWorkbenchTaskRequest,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "notification:write")
        tenant_id = _current_tenant_id(user)
        tasks = _ensure_workbench_tasks(ctx, tenant_id=tenant_id)
        target = next((item for item in tasks if item.get("id") == task_id), None)
        if target is None:
            raise HTTPException(status_code=404, detail="Task not found")
        target["last_nudge_at"] = _now_iso()
        target["last_nudge_by"] = user.get("id")
        target["last_nudge_target_role"] = payload.target_role or ""
        target["last_nudge_message"] = payload.message or ""
        target["updated_at"] = _now_iso()
        _save_workbench_tasks(ctx, tenant_id, tasks)
        return _ok(
            {
                "ok": True,
                "status": "nudged",
                "message": "nudge sent",
                "task_id": target.get("id"),
                "dispatch_id": target.get("dispatch_id") or "",
            }
        )

    @fastapi_app.post("/api/notifications/send")
    def send_notification(
        payload: NotificationSendRequest,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "notification:write")
        template = None
        tenant_id = _current_tenant_id(user)
        if payload.template_id:
            template = ctx.template_service.get_notification_template(
                payload.template_id, tenant_id=tenant_id
            )
            if template is None:
                raise HTTPException(status_code=404, detail="Template not found")
        if template is None:
            template = next(
                (
                    item
                    for item in ctx.template_service.list_notification_templates(
                        tenant_id=tenant_id
                    )
                    if item.is_active
                ),
                ctx.template_service.ensure_default_template(tenant_id=tenant_id),
            )

        destination = payload.destination or "未指定行程"
        team_id = _resolve_team_id(payload.team, payload.team_id)
        trip_label = payload.trip or payload.trip_id or ""
        if payload.trip_id:
            trip = ctx.trip_repository.get(payload.trip_id)
            if trip is not None:
                assert_trip_access(user, trip)
                destination = trip.get("destination", destination)
                team_id = str(trip.get("team_id") or trip.get("team") or team_id)
                trip_label = str(trip.get("destination") or trip_label or payload.trip_id)

        if payload.custom_content:
            rendered = payload.custom_content
        else:
            rendered = ctx.template_service.render_notification(
                template,
                {
                    "customer_name": payload.customer_name or user.get("username", user["id"]),
                    "destination": destination,
                },
            )
        task = NotificationTask(
            tenant_id=tenant_id,
            team_id=team_id,
            trip_id=trip_label,
            customer_id=payload.customer_phone or user["id"],
            rendered_content=rendered,
            idempotency_key=f"manual:{uuid4().hex}",
            primary_channel=_parse_channel(payload.channel),
            fallback_channel=Channel.WECHAT_WORK_GROUP,
            provider_context={
                "customer_name": payload.customer_name or user.get("username", user["id"]),
                "trip_label": trip_label,
            },
        )
        ctx.notification_tasks[task.id] = task
        if payload.async_delivery:
            job = ctx.async_dispatch_service.enqueue(task, channel=task.primary_channel.value)
            dispatch_result = {"ok": True, "reason": "queued", "job_id": job.job_id}
        else:
            dispatch_result = ctx.notification_service.dispatch(task)
        ctx.audit_service.record(
            operator_id=user["id"],
            action="notification_dispatched",
            target=payload.trip_id or "manual",
            detail={
                "ok": dispatch_result["ok"],
                "attempts": len(task.attempts),
                "async_delivery": payload.async_delivery,
            },
        )
        response = {
            "ok": dispatch_result["ok"],
            "notification_id": task.id,
            "status": task.status.value,
        }
        if "job_id" in dispatch_result:
            response["job_id"] = dispatch_result["job_id"]
        return _ok(response)

    @fastapi_app.get("/api/notifications/emergency-weather")
    def get_emergency_weather_summary(
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "notification:read")
        service = _build_emergency_weather_service(ctx)
        return _ok(service.get_summary(_current_tenant_id(user)))

    @fastapi_app.post("/api/notifications/emergency-weather/send")
    def send_emergency_weather_notification(
        payload: EmergencyWeatherSendRequest,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "notification:write")
        service = _build_emergency_weather_service(ctx)
        result = service.send_summary(
            tenant_id=_current_tenant_id(user),
            operator_id=user["id"],
            custom_content=payload.custom_content,
            channel=payload.channel,
        )
        ctx.audit_service.record(
            operator_id=user["id"],
            action="emergency_weather_notification_sent",
            target=payload.alert_id,
            detail={
                "channel": payload.channel,
                "content_length": len((payload.custom_content or "").strip()),
                "status": result["status"],
            },
        )
        return _ok(result)

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
        tenant_id = _current_tenant_id(user)
        resolved_team_id = _resolve_team_id(team, team_id)
        items = _query_notification_items(
            repository=ctx.notification_attempt_repository,
            limit=limit,
            trip_id=trip_id,
            team_id=resolved_team_id or None,
            customer_id=customer_id,
            tenant_id=tenant_id,
            channel=channel,
            status=status,
        )
        return _ok({"total": len(items), "items": items})

    @fastapi_app.get("/api/notifications/jobs")
    def list_notification_jobs(
        limit: int = 50,
        trip_id: str | None = None,
        team_id: str | None = None,
        team: str | None = None,
        status: str | None = None,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "notification:read")
        tenant_id = _current_tenant_id(user)
        resolved_team_id = _resolve_team_id(team, team_id)
        items = ctx.async_dispatch_service.list_jobs(
            tenant_id=tenant_id,
            team_id=resolved_team_id or None,
            trip_id=trip_id,
            status=status,
            limit=limit,
        )
        return _ok({"total": len(items), "items": items})

    @fastapi_app.post("/api/notifications/jobs/run")
    def run_notification_jobs(
        user: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "notification:write")
        items = ctx.async_dispatch_service.run_due_jobs(ctx.notification_tasks)
        return _ok({"processed": len(items), "items": items})

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
        tenant_id = _current_tenant_id(user)
        resolved_team_id = _resolve_team_id(team, team_id)
        dashboard_service = DashboardService(
            trip_repository=ctx.trip_repository,
            notification_attempt_repository=ctx.notification_attempt_repository,
            template_service=ctx.template_service,
        )
        if trip_id or resolved_team_id or customer_id or channel or status:
            items = _query_notification_items(
                repository=ctx.notification_attempt_repository,
                limit=limit,
                trip_id=trip_id,
                team_id=resolved_team_id or None,
                customer_id=customer_id,
                tenant_id=tenant_id,
                channel=channel,
                status=status,
            )
            recent = [_to_recent_item(item) for item in items]
        else:
            recent = dashboard_service.get_recent_items(tenant_id=tenant_id, limit=limit)
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
            tenant_id=_current_tenant_id(user),
        )
        logs = ctx.audit_service.repository.list_by_target_payload(trip_id)
        return _ok(
            {"trip": _serialize_trip(trip), "notification_attempts": attempts, "audit_logs": logs}
        )

    @fastapi_app.get("/api/dashboard/stats")
    def dashboard_stats(
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        tenant_id = _current_tenant_id(user)
        dashboard_service = DashboardService(
            trip_repository=ctx.trip_repository,
            notification_attempt_repository=ctx.notification_attempt_repository,
            template_service=ctx.template_service,
        )
        return _ok(
            dashboard_service.get_stats(
                tenant_id=tenant_id, total_users=len(ctx.auth_service.users)
            )
        )

    @fastapi_app.get("/api/dashboard/smart-suggestions")
    def dashboard_smart_suggestions(
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        dashboard_service = DashboardService(
            trip_repository=ctx.trip_repository,
            notification_attempt_repository=ctx.notification_attempt_repository,
            template_service=ctx.template_service,
        )
        return _ok(dashboard_service.get_smart_suggestions(tenant_id=_current_tenant_id(user)))

    @fastapi_app.post("/api/admin/run-automation-scan")
    def run_automation_scan(
        user: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        orchestrator = WorkflowOrchestrator(
            trip_repository=ctx.trip_repository,
            template_service=ctx.template_service,
            notification_service=ctx.notification_service,
        )
        result = orchestrator.scan_and_trigger(tenant_id=_current_tenant_id(user))
        return _ok(result)

    @fastapi_app.post("/api/admin/trigger-weather-check")
    def trigger_weather_check(
        user: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        active_trips = [t for t in ctx.trip_repository.list() if t.get("status") == "in_progress"]
        triggered_count = 0

        for trip in active_trips:
            project_id = str(
                trip.get("project_id") or trip.get("team_id") or trip.get("team") or ""
            )
            project_config = ctx.project_notification_config_repository.get(
                project_id,
                tenant_id=_current_tenant_id(user),
            )
            weather_context = dict(project_config or {})
            weather_context.update(trip)
            info = ctx.weather_provider.get_weather(
                str(trip.get("destination", "")),
                location_context=weather_context,
            )
            if info.warning_level:
                # 命中恶劣天气，触发通知
                rendered = f"【天气预警】您在 {info.destination} 的行程受 {info.condition} 影响，当前气温 {info.temperature}C，请注意安全。"
                task = NotificationTask(
                    tenant_id=_current_tenant_id(user),
                    project_id=project_id,
                    team_id=str(trip.get("team_id", "")),
                    trip_id=str(trip.get("id", "")),
                    customer_id="system",
                    rendered_content=rendered,
                    idempotency_key=f"weather:{trip.get('id')}:{datetime.now().date()}",
                    primary_channel=Channel.SMS,
                )
                ctx.notification_tasks[task.id] = task
                ctx.notification_service.dispatch(task)
                triggered_count += 1

        return _ok(
            {"active_trips_checked": len(active_trips), "triggered_notifications": triggered_count}
        )

    @fastapi_app.get("/api/analytics/metrics")
    def analytics_metrics(
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        snapshot = ctx.analytics_service.build_metrics_snapshot()
        tenant_id = _current_tenant_id(user)
        attempts = _query_notification_items(
            repository=ctx.notification_attempt_repository,
            limit=9999,
            trip_id=None,
            team_id=None,
            customer_id=None,
            tenant_id=tenant_id,
        )
        if not attempts:
            facts = ctx.analytics_service.repository.list_notification_facts()
            attempts = [
                {
                    "channel": str(item.get("channel") or "sms"),
                    "ok": bool(item.get("success")),
                    "attempt_no": 1,
                    "status": "sent" if bool(item.get("success")) else "failed",
                    "latency_ms": int(item.get("latency_ms") or 0),
                    "trip_id": str(item.get("trip_id") or ""),
                    "attempted_at": f"{item.get('event_date')}T00:00:00+00:00",
                }
                for item in facts
            ]
        total = len(attempts)
        successful = sum(1 for item in attempts if item.get("ok") is True)
        failed = total - successful
        retried = sum(1 for item in attempts if int(item.get("attempt_no", 1)) > 1)
        manual_takeover = sum(
            1 for item in attempts if str(item.get("status") or "") == "manual_intervention"
        )
        avg_latency = (
            round(
                sum(int(item.get("latency_ms", 0)) for item in attempts) / total,
                1,
            )
            if total
            else 0.0
        )

        feedbacks = ctx.analytics_service.repository.list_feedbacks()
        avg_satisfaction = (
            sum(float(item.get("score", 0.0)) for item in feedbacks) / len(feedbacks)
            if feedbacks
            else 0.0
        )

        payload = {
            "metrics": {
                "notification_success_rate": f"{round((successful / total) * 100, 1) if total else 0.0}%",
                "notification_retry_rate": f"{round((retried / total) * 100, 1) if total else 0.0}%",
                "notification_manual_takeover_rate": (
                    f"{round((manual_takeover / total) * 100, 1) if total else 0.0}%"
                ),
                "rule_publish_lead_time": "0h",
                "cross_tenant_forbidden_count": 0,
                "avg_response_time": f"{avg_latency}ms",
                "user_satisfaction": f"{round(avg_satisfaction, 1) if feedbacks else 0.0}/5",
                "total_notifications": total,
                "successful_notifications": successful,
                "failed_notifications": failed,
                "wow_growth": snapshot.get("summary", {}).get("wow_growth", 0.0),
            },
            "channel_performance": _compute_channel_performance(attempts),
            "top_trips": _compute_top_trips(attempts, ctx.trip_repository),
            "summary": snapshot.get("summary", {}),
            "charts": snapshot.get("charts", {}),
        }
        analytics_view_service = AnalyticsViewService(
            analytics_service=ctx.analytics_service,
            trip_repository=ctx.trip_repository,
        )
        return _ok(
            analytics_view_service.build_metrics_payload(
                payload,
                tenant_id=tenant_id,
            )
        )

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
