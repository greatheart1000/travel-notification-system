from __future__ import annotations

import csv
import io
import os
import re
import zipfile
from dataclasses import asdict, dataclass
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
from app.core.models import Channel, NotificationType
from app.core.observability import metrics, new_trace_id, reset_trace_id, set_trace_context
from app.modules.analytics.service import AnalyticsRepository, AnalyticsService
from app.modules.audit.service import AuditLogRepository, AuditService
from app.modules.integration.auth import AuthService
from app.modules.integration.wechat_provider import get_wechat_provider_for_trip
from app.modules.integration.persistence import (
    JsonFileStore,
    ProjectNotificationConfigRepository,
    TripRepository,
    WorkflowExecutionRepository,
)
from app.modules.integration.rbac import PermissionDenied, assert_tenant_scope, require_permission
from app.modules.integration.weather_provider import WeatherProvider
from app.modules.notification.concierge_playbook import MESSAGE_TEMPLATES
from app.modules.notification.idempotency import IdempotencyStore
from app.modules.notification.models import NotificationTask
from app.modules.notification.rule_service import NotificationRuleRepository, RuleValidationError
from app.modules.notification.provider_registry import (
    TenantNotificationConfigRepository,
    TenantProviderRegistry,
)
from app.modules.notification.service import NotificationAttemptRepository, NotificationService
from app.modules.trigger.risk_alert_service import RiskAlertService
from app.services.analytics_view_service import AnalyticsViewService
from app.services.async_dispatch import AsyncDispatchService
from app.services.emergency_weather_service import EmergencyWeatherService
from app.services.notification_agent_service import NotificationAgentService
from app.services.preference_service import UserPreferenceService
from app.services.risk_notification_service import RiskEvidenceRepository, RiskNotificationWorkflow
from app.services.scheduler_service import init_scheduler
from app.services.template_service import TemplateService
from app.services.workflow_orchestrator import WorkflowOrchestrator

UTC = UTC




def _parse_optional_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid datetime") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed

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
    tenant_notification_config_repository: TenantNotificationConfigRepository
    idempotency_store: IdempotencyStore
    async_dispatch_service: AsyncDispatchService
    audit_service: AuditService
    analytics_service: AnalyticsService
    weather_provider: WeatherProvider
    risk_evidence_repository: RiskEvidenceRepository
    notification_tasks: dict[str, NotificationTask]
    scheduler_service: Any | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class PreferenceUpdateRequest(BaseModel):
    channels: list[str] = Field(default_factory=list, max_length=5)
    quiet_hours: list[int] = Field(default_factory=lambda: [23, 7], min_length=2, max_length=2)
    max_notifications_per_hour: int | None = Field(default=None, ge=0, le=100)
    auto_escalation: bool | None = None
    aggregate_notifications: bool | None = None
    allow_marketing: bool | None = None

    @field_validator("channels")
    @classmethod
    def check_channels(cls, v: list[str]) -> list[str]:
        for c in v:
            if c not in ("sms", "wechat_work_group", "email"):
                raise ValueError(f"无效渠道: {c}，可选: sms, wechat_work_group, email")
        return v

    @field_validator("quiet_hours")
    @classmethod
    def check_quiet_hours(cls, v: list[int]) -> list[int]:
        if not (0 <= v[0] <= 23 and 0 <= v[1] <= 23):
            raise ValueError("静音时段必须在 0-23 之间")
        return v


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
    trip_id: str | None = None


class NotificationRuleUpdateRequest(BaseModel):
    name: str | None = None
    stage: str | None = None
    time_slot: str | None = None
    scene: str | None = None
    channels: list[str] | None = None
    template_id: str | None = None
    enabled: bool | None = None
    trip_id: str | None = None
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
    destination: str = Field(min_length=1, max_length=100)
    team: str | None = Field(default=None, min_length=1, max_length=64)
    team_id: str | None = Field(default=None, min_length=1, max_length=64)
    start_date: str = Field(min_length=8, max_length=10)
    end_date: str = Field(min_length=8, max_length=10)
    participants: int = Field(default=1, ge=0, le=10000)
    status: str = "planned"

    @field_validator("participants")
    @classmethod
    def check_participants(cls, v: int) -> int:
        if v < 0: raise ValueError("人数不能为负数")
        return v

    @field_validator("end_date")
    @classmethod
    def check_dates(cls, v: str, info) -> str:
        start = info.data.get("start_date")
        if start and v and v < start:
            raise ValueError("结束日期不能早于开始日期")
        return v


class TripUpdateRequest(BaseModel):
    destination: str | None = Field(default=None, min_length=1, max_length=100)
    team: str | None = Field(default=None, min_length=1, max_length=64)
    team_id: str | None = Field(default=None, min_length=1, max_length=64)
    start_date: str | None = None
    end_date: str | None = None
    participants: int | None = Field(default=None, ge=0, le=10000)
    status: str | None = None
    leader_name: str | None = Field(default=None, max_length=64)
    contact_phone: str | None = Field(default=None, max_length=20)
    itinerary: list[dict[str, Any]] | None = None
    guests: list[dict[str, Any]] | None = None

    @field_validator("participants")
    @classmethod
    def check_participants(cls, v: int | None) -> int | None:
        if v is not None and v < 0: raise ValueError("人数不能为负数")
        return v

    @field_validator("team", "team_id", "leader_name", "contact_phone")
    @classmethod
    def validate_team_fields(cls, value: str | None) -> str | None:
        if value is None: return value
        return value.strip()


class TripImportValidationApplyRequest(BaseModel):
    fields: dict[str, str] = Field(default_factory=dict)


class ERPImportMealFlags(BaseModel):
    breakfast: bool = False
    lunch: bool = False
    dinner: bool = False


class ERPImportGroupRequest(BaseModel):
    group_no: str = ""
    line_name: str = ""
    departure_date_start: date | None = None
    departure_date_end: date | None = None
    operator: str = ""
    sales: str = ""
    people_count: int | None = None
    people_count_text: str = ""
    guest_source: str = ""
    outbound_transport: str = ""
    return_transport: str = ""
    assembly_location: str = ""
    dismiss_location: str = ""
    guide: str = ""
    agency_group_no: str = ""
    team_social_group_no: str = ""


class ERPImportItineraryDayRequest(BaseModel):
    date: date
    date_text: str = ""
    day_index: int = 0
    transport: str = ""
    route: str = ""
    breakfast: bool = False
    lunch: bool = False
    dinner: bool = False
    meals: ERPImportMealFlags | None = None
    breakfast_text: str = ""
    lunch_text: str = ""
    dinner_text: str = ""
    hotel: str = ""
    remark: str = ""


class ERPImportGuestRequest(BaseModel):
    guest_id: str = ""
    name: str = ""
    phone: str = ""
    id_card: str = ""
    gender: str = ""
    age: int | None = None
    role: str = "guest"
    remark: str = ""


class ERPImportTransferRequest(BaseModel):
    operation: str = ""
    type: str = ""
    date: date
    date_text: str = ""
    location: str = ""
    flight_or_train_no: str = ""
    time: str = ""
    raw_shift_text: str = ""
    description: str = ""


class ERPImportReportMetaRequest(BaseModel):
    report_title: str = ""
    report_generated_at: str = ""
    print_person: str = ""
    print_phone: str = ""
    print_mobile: str = ""
    print_date: date | None = None
    source_url: str = ""
    source_file_name: str = ""
    page_count: int = 0


class ERPImportWarningRequest(BaseModel):
    field: str = ""
    message: str


class ERPImportDataRequest(BaseModel):
    group: ERPImportGroupRequest
    itinerary_days: list[ERPImportItineraryDayRequest] = Field(default_factory=list)
    guests: list[ERPImportGuestRequest] = Field(default_factory=list)
    transfers: list[ERPImportTransferRequest] = Field(default_factory=list)
    report_meta: ERPImportReportMetaRequest = Field(default_factory=ERPImportReportMetaRequest)


class ERPImportReportRequest(BaseModel):
    success: bool = True
    message: str = ""
    data: ERPImportDataRequest
    warnings: list[ERPImportWarningRequest] = Field(default_factory=list)


class NotificationSendRequest(BaseModel):
    template_id: str | None = None
    trip_id: str | None = None
    trip: str | None = None
    team: str | None = None
    team_id: str | None = None
    customer_name: str | None = Field(default=None, max_length=64)
    customer_phone: str | None = Field(default=None, max_length=20, min_length=7)
    custom_content: str | None = Field(default=None, max_length=5000)
    destination: str | None = None
    channel: str = "sms"
    async_delivery: bool = False


class EmergencyWeatherSendRequest(BaseModel):
    alert_id: str = Field(min_length=1, max_length=64)
    custom_content: str | None = Field(default=None, max_length=5000)
    channel: str = "sms"

    @field_validator("channel")
    @classmethod
    def check_channel(cls, v: str) -> str:
        if v not in ("sms", "wechat_work_group", "email"):
            raise ValueError(f"无效渠道: {v}")
        return v


VALID_TIME_SLOTS = ("morning", "afternoon", "evening", "night", "all_day")
VALID_CHANNELS = ("sms", "wechat_work_group", "email")

class DispatchPreviewRequest(BaseModel):
    trip_id: str = Field(min_length=1)
    node_key: str = Field(min_length=1, max_length=64)
    channel: str = "sms"
    channel_code: str | None = None
    template_id: str | None = None

    @field_validator("channel")
    @classmethod
    def check_channel(cls, v: str) -> str:
        if v not in VALID_CHANNELS:
            raise ValueError(f"无效渠道: {v}")
        return v


class DispatchNowRequest(BaseModel):
    trip_id: str = Field(min_length=1)
    node_key: str = Field(min_length=1, max_length=64)
    channel: str = "sms"
    channel_code: str | None = None
    template_id: str | None = None
    content: str | None = Field(default=None, max_length=5000)

    @field_validator("channel")
    @classmethod
    def check_channel(cls, v: str) -> str:
        if v not in VALID_CHANNELS:
            raise ValueError(f"无效渠道: {v}")
        return v


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


class TenantNotificationConfigUpsertRequest(BaseModel):
    wechat_webhook_url: str = ""
    sms_provider: str = ""
    sms_sign_name: str = ""
    sms_template_code: str = ""
    sms_credential_id: str = ""

    @field_validator("sms_provider")
    @classmethod
    def check_sms_provider(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"", "mock", "aliyun"}:
            raise ValueError("sms_provider must be one of: mock, aliyun")
        return normalized


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


def _build_trip_patch_from_erp_report(payload: ERPImportReportRequest) -> dict[str, Any]:
    group = payload.data.group

    def _meal_flag(item: ERPImportItineraryDayRequest, name: str) -> bool:
        direct = getattr(item, name)
        if direct:
            return True
        if item.meals is None:
            return False
        return bool(getattr(item.meals, name))

    itinerary = [
        {
            "date": item.date.isoformat(),
            "date_text": item.date_text,
            "day_index": item.day_index,
            "transport": item.transport,
            "route": item.route,
            "breakfast": _meal_flag(item, "breakfast"),
            "lunch": _meal_flag(item, "lunch"),
            "dinner": _meal_flag(item, "dinner"),
            "breakfast_text": item.breakfast_text,
            "lunch_text": item.lunch_text,
            "dinner_text": item.dinner_text,
            "hotel": item.hotel,
            "remark": item.remark,
        }
        for item in payload.data.itinerary_days
    ]
    guests = [
        {
            "guest_id": item.guest_id,
            "name": item.name,
            "phone": item.phone,
            "id_card": item.id_card,
            "gender": item.gender,
            "age": item.age,
            "role": item.role,
            "remark": item.remark,
        }
        for item in payload.data.guests
    ]
    transfers = [
        {
            "operation": item.operation,
            "type": item.type,
            "date": item.date.isoformat(),
            "date_text": item.date_text,
            "location": item.location,
            "flight_or_train_no": item.flight_or_train_no,
            "time": item.time,
            "raw_shift_text": item.raw_shift_text,
            "description": item.description,
        }
        for item in payload.data.transfers
    ]
    report_meta = {
        "report_title": payload.data.report_meta.report_title,
        "report_generated_at": payload.data.report_meta.report_generated_at,
        "print_person": payload.data.report_meta.print_person,
        "print_phone": payload.data.report_meta.print_phone,
        "print_mobile": payload.data.report_meta.print_mobile,
        "print_date": (
            payload.data.report_meta.print_date.isoformat()
            if payload.data.report_meta.print_date
            else ""
        ),
        "source_url": payload.data.report_meta.source_url,
        "source_file_name": payload.data.report_meta.source_file_name,
        "page_count": payload.data.report_meta.page_count,
    }
    warnings = [{"field": item.field, "message": item.message} for item in payload.warnings]

    return {
        "destination": group.line_name,
        "team_id": group.group_no,
        "start_date": group.departure_date_start.isoformat() if group.departure_date_start else "",
        "end_date": group.departure_date_end.isoformat() if group.departure_date_end else "",
        "participants": int(group.people_count or len(guests) or 0),
        "leader_name": guests[0].get("name", "") if guests else "",
        "contact_phone": guests[0].get("phone", "") if guests else "",
        "itinerary": itinerary,
        "guests": guests,
        "transfers": transfers,
        "erp_group": group.model_dump(mode="json"),
        "erp_report_meta": report_meta,
        "erp_report_warnings": warnings,
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
    transfers = trip.get("transfers") if isinstance(trip.get("transfers"), list) else []
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
        "leader_name": str(trip.get("leader_name") or trip.get("trip_manager_name") or ""),
        "contact_phone": str(trip.get("contact_phone") or ""),
        "trip_manager_name": str(trip.get("trip_manager_name") or ""),
        "trip_manager_phone": str(trip.get("trip_manager_phone") or ""),
        "concierge_name": str(trip.get("concierge_name") or ""),
        "concierge_phone": str(trip.get("concierge_phone") or ""),
        "driver_name": str(trip.get("driver_name") or ""),
        "driver_phone": str(trip.get("driver_phone") or ""),
        "webhook_url": str(trip.get("webhook_url") or ""),
        "wecom_chat_id": str(trip.get("wecom_chat_id") or ""),
        "itinerary": itinerary,
        "guests": guests,
        "transfers": transfers,
        "erp_group": trip.get("erp_group", {}),
        "erp_report_meta": trip.get("erp_report_meta", {}),
        "erp_report_warnings": trip.get("erp_report_warnings", []),
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
                "trip_id": trip_id,
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
    tenant_notification_config_repository = TenantNotificationConfigRepository(store=persistence)
    provider_registry = TenantProviderRegistry(
        config_repository=tenant_notification_config_repository
    )
    notification_service = NotificationService(
        idempotency_store=IdempotencyStore(store=persistence),
        attempt_repository=notification_attempt_repository,
        provider_registry=provider_registry,
    )
    async_dispatch_service = AsyncDispatchService(
        notification_service=notification_service,
        store=persistence,
    )
    audit_service = AuditService(repository=AuditLogRepository(store=persistence))
    analytics_service = AnalyticsService(
        repository=AnalyticsRepository(store=persistence),
        attempt_repository=notification_attempt_repository,
        trip_repository=trip_repository,
    )
    auth_service = AuthService()
    weather_provider = WeatherProvider()
    risk_evidence_repository = RiskEvidenceRepository(store=persistence)
    context = AppContext(
        store=persistence,
        auth_service=auth_service,
        trip_repository=trip_repository,
        project_notification_config_repository=project_notification_config_repository,
        template_service=template_service,
        preference_service=preference_service,
        notification_attempt_repository=notification_attempt_repository,
        notification_rule_repository=notification_rule_repository,
        notification_service=notification_service,
        tenant_notification_config_repository=tenant_notification_config_repository,
        idempotency_store=notification_service.idempotency_store,
        async_dispatch_service=async_dispatch_service,
        audit_service=audit_service,
        analytics_service=analytics_service,
        weather_provider=weather_provider,
        risk_evidence_repository=risk_evidence_repository,
        notification_tasks={},
    )
    context.scheduler_service = init_scheduler(context)
    return context



def _build_risk_notification_workflow(ctx: AppContext) -> RiskNotificationWorkflow:
    return RiskNotificationWorkflow(
        trip_repository=ctx.trip_repository,
        template_service=ctx.template_service,
        notification_service=ctx.notification_service,
        weather_provider=ctx.weather_provider,
        evidence_repository=ctx.risk_evidence_repository,
        audit_service=ctx.audit_service,
        project_notification_config_repository=ctx.project_notification_config_repository,
    )

def create_app() -> FastAPI:
    _patch_starlette_router_compat()

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        ctx = app.state.ctx
        scheduler = ctx.scheduler_service or init_scheduler(ctx)
        ctx.scheduler_service = scheduler
        scheduler.start()
        yield
        scheduler.stop()

    fastapi_app = FastAPI(
        title="Travel Notification API",
        version="0.2.0",
        lifespan=lifespan,
    )

    @fastapi_app.middleware("http")
    async def trace_middleware(request: Request, call_next):
        incoming = request.headers.get("X-Trace-Id") or new_trace_id()
        trace_id, token = set_trace_context(incoming)
        try:
            response = await call_next(request)
        finally:
            reset_trace_id(token)
        response.headers["X-Trace-Id"] = trace_id
        return response

    from fastapi.middleware.gzip import GZipMiddleware
    fastapi_app.add_middleware(GZipMiddleware, minimum_size=500)
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

    @fastapi_app.get("/api/health/metrics")
    def get_metrics() -> dict[str, Any]:
        return _ok(metrics.snapshot())

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

    @fastapi_app.get("/api/risk-notifications/triggers")
    def list_risk_notification_triggers(
        now: str | None = None,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "notification:read")
        current = _parse_optional_datetime(now)
        workflow = _build_risk_notification_workflow(ctx)
        triggers = workflow.build_triggers(tenant_id=_current_tenant_id(user), now=current)
        return _ok({"items": [asdict(trigger) for trigger in triggers]})

    @fastapi_app.post("/api/risk-notifications/run")
    def run_risk_notifications(
        now: str | None = None,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "notification:write")
        current = _parse_optional_datetime(now)
        workflow = _build_risk_notification_workflow(ctx)
        result = workflow.send_due_risks(tenant_id=_current_tenant_id(user), now=current)
        return _ok(result)

    @fastapi_app.get("/api/risk-notifications/evidence")
    def list_risk_notification_evidence(
        trip_id: str | None = None,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "notification:read")
        return _ok(
            {
                "items": ctx.risk_evidence_repository.list(
                    tenant_id=_current_tenant_id(user),
                    trip_id=trip_id,
                )
            }
        )

    @fastapi_app.post("/api/risk-notifications/evidence/{evidence_id}/confirm")
    def confirm_risk_notification_evidence(
        evidence_id: str,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "notification:write")
        workflow = _build_risk_notification_workflow(ctx)
        try:
            return _ok(
                workflow.confirm(
                    evidence_id,
                    tenant_id=_current_tenant_id(user),
                    operator_id=user["id"],
                )
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Evidence not found") from exc

    @fastapi_app.post("/api/risk-notifications/escalate-overdue")
    def escalate_overdue_risk_notifications(
        timeout_minutes: int = 15,
        now: str | None = None,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "ops:read")
        workflow = _build_risk_notification_workflow(ctx)
        items = workflow.escalate_overdue(
            tenant_id=_current_tenant_id(user),
            now=_parse_optional_datetime(now),
            timeout_minutes=timeout_minutes,
        )
        return _ok({"escalated_count": len(items), "items": items})

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
        trip = _find_trip(trip_id, ctx)
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
        total = len(items)
        page = int(kwargs.get("page", 1)) if "page" in str(locals().get("kwargs",{})) else 1
        page_size = int(kwargs.get("page_size", 0)) if "page_size" in str(locals().get("kwargs",{})) else 0
        if page_size > 0:
            items = items[(page-1)*page_size : (page-1)*page_size + page_size]
        normalized_items = [_serialize_trip(item) for item in items]
        return _ok({"total": total, "items": normalized_items})

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

        # Trip creation has no guest recipient yet. Do not send an SMS to the
        # operator's user id; notifications are dispatched later from the trip
        # notification rules once guests/phones are known.
        ctx.audit_service.record(
            operator_id=user["id"],
            action="trip_created",
            target=trip_id,
            detail={"destination": payload.destination, "team_id": team_id},
        )
        return {
            "trip": _serialize_trip(trip),
            "notification": {
                "ok": True,
                "status": "skipped",
                "attempt_count": 0,
                "reason": "trip_created_without_recipient",
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

    @fastapi_app.post("/api/erp/import-report")
    def import_erp_report(
        payload: ERPImportReportRequest,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "trip:write")
        trip_payload = _build_trip_patch_from_erp_report(payload)
        created = create_trip_record(
            payload=TripCreateRequest(
                destination=str(trip_payload["destination"]),
                team_id=str(trip_payload["team_id"]),
                start_date=str(trip_payload["start_date"]),
                end_date=str(trip_payload["end_date"]),
                participants=int(trip_payload["participants"]),
                status="计划中",
            ),
            user=user,
            ctx=ctx,
        )
        trip = created["trip"]
        patch = {
            "itinerary": trip_payload["itinerary"],
            "guests": trip_payload["guests"],
            "participants": max(int(trip_payload["participants"]), len(trip_payload["guests"])),
            "leader_name": trip_payload["leader_name"],
            "contact_phone": trip_payload["contact_phone"],
            "transfers": trip_payload["transfers"],
            "erp_group": trip_payload["erp_group"],
            "erp_report_meta": trip_payload["erp_report_meta"],
            "erp_report_warnings": trip_payload["erp_report_warnings"],
        }
        updated = ctx.trip_repository.update(trip["id"], patch)
        return _ok(
            {
                "created_count": 1,
                "skipped_count": 0,
                "items": [_serialize_trip(updated or trip)],
                "erp_report": payload.model_dump(mode="json"),
            }
        )

    @fastapi_app.get("/api/trips/{trip_id}")
    def get_trip(
        trip_id: str,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        trip = _find_trip(trip_id, ctx)
        if trip is None:
            for t in ctx.trip_repository.list():
                if str(t.get("team_id") or t.get("team") or "") == trip_id:
                    trip = t; break
        if trip is None:
            raise HTTPException(status_code=404, detail="Trip not found")
        assert_trip_access(user, trip)
        return _ok(_serialize_trip(trip))

    # ═══ 企业微信回调验证 ═══
    @fastapi_app.api_route("/api/wecom/callback", methods=["GET", "POST"])
    async def wecom_callback(request: Request):
        """企业微信回调 URL 验证 + 接收消息。"""
        import hashlib, base64, struct
        params = dict(request.query_params)
        msg_sig = params.get("msg_signature", "")
        timestamp = params.get("timestamp", "")
        nonce = params.get("nonce", "")
        echostr = params.get("echostr", "")
        from fastapi.responses import PlainTextResponse

        if echostr:
            try:
                from Crypto.Cipher import AES
                token = os.getenv("WECOM_TOKEN", "UKES")
                aes_enc = os.getenv("WECOM_ENCODING_AES_KEY", "qG7yl4k2FKcmHydXlq6xNOh1faj262KJK7rRtc3tgY5")
                aes_key = base64.b64decode(aes_enc + "=")
                raw = "".join(sorted([token, timestamp, nonce, echostr]))
                sig = hashlib.sha1(raw.encode()).hexdigest()
                if sig == msg_sig:
                    cipher = AES.new(aes_key, AES.MODE_CBC, aes_key[:16])
                    dec = cipher.decrypt(base64.b64decode(echostr))
                    pad = dec[-1]
                    dec = dec[:-pad]
                    length = struct.unpack(">I", dec[16:20])[0]
                    result = dec[20:20+length].decode("utf-8")
                    return PlainTextResponse(result)
            except Exception:
                pass
            # 明文模式回退
            return PlainTextResponse(echostr)

        body = await request.body()
        return {"code": 200}

    # ═══ 企业微信群管理 ═══
    @fastapi_app.put("/api/trips/{trip_id}/webhook")
    def set_trip_webhook(trip_id: str, body: dict[str, Any], user=Depends(get_current_user), ctx=Depends(get_ctx)):
        _require_permission_or_403(user, "notification:write")
        trip = _find_trip(trip_id, ctx)
        if trip is None: raise HTTPException(404, "Trip not found")
        assert_trip_access(user, trip)
        ctx.trip_repository.update(str(trip.get("id","")), {"webhook_url": str(body.get("webhook_url",""))})
        ctx.audit_service.record(operator_id=user["id"], action="webhook_updated", target=trip_id)
        return _ok({"trip_id": trip_id, "message": "企业微信群已配置"})

    @fastapi_app.post("/api/trips/{trip_id}/webhook/test")
    def test_trip_webhook(trip_id: str, user=Depends(get_current_user), ctx=Depends(get_ctx)):
        """发送测试消息到行程配置的企业微信群。"""
        _require_permission_or_403(user, "notification:write")
        trip = _find_trip(trip_id, ctx)
        if trip is None: raise HTTPException(404, "Trip not found")
        assert_trip_access(user, trip)
        webhook_url = str(trip.get("webhook_url", "")).strip()
        if not webhook_url:
            raise HTTPException(400, "请先配置企业微信群 webhook 地址")
        from zoneinfo import ZoneInfo
        now = datetime.now(tz=ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")
        content = f"【{now}】\n✅ 企业微信群机器人连接测试成功！\n行程：{trip.get('destination', '')}\n团号：{trip.get('team_id') or trip.get('team', '')}\n\n您好，这是一条来自旅行通知系统的测试消息，如果您能收到此消息，说明群机器人配置正确，后续通知将正常推送。"
        provider = get_wechat_provider_for_trip(trip)
        ok, msg = provider.send(f"test:{trip_id}", content)
        if not ok:
            raise HTTPException(502, f"测试发送失败: {msg}")
        ctx.audit_service.record(operator_id=user["id"], action="webhook_tested", target=trip_id)
        return _ok({"trip_id": trip_id, "message": "测试消息已发送，请查看企业微信群"})

    @fastapi_app.post("/api/trips/{trip_id}/create-group")
    def create_wecom_group(trip_id: str, user=Depends(get_current_user), ctx=Depends(get_ctx)):
        """为企业微信创建行程专属服务群，并自动拉入游客和工作人员。"""
        _require_permission_or_403(user, "notification:write")
        trip = _find_trip(trip_id, ctx)
        if trip is None: raise HTTPException(404, "Trip not found")
        assert_trip_access(user, trip)
        try:
            from app.modules.integration.wecom_api import create_group
            # 生成群名
            dest = trip.get("destination", "旅行团")
            code = trip.get("team_id") or trip.get("team") or trip.get("id","")
            group_name = f"{dest}-{code}-服务群"
            # 收集游客 + 工作人员 userid（先用 phone 占位）
            member_ids: list[str] = []
            for g in trip.get("guests", [])[:50]:
                phone = str(g.get("phone","")).strip()
                if phone: member_ids.append(phone)
            # 添加工作人员
            for role_phone in [trip.get("trip_manager_phone",""), trip.get("concierge_phone",""), trip.get("driver_phone","")]:
                if role_phone and role_phone not in member_ids:
                    member_ids.insert(0, role_phone)
            result = create_group(group_name, member_ids[:2000])
            chat_id = result.get("chatid", "")
            # 保存 chat_id 和 webhook_url 到行程
            wh_url = result.get("webhook_url", "") or f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={chat_id}"
            ctx.trip_repository.update(str(trip.get("id","")), {"wecom_chat_id": chat_id, "webhook_url": wh_url})
            ctx.audit_service.record(operator_id=user["id"], action="wecom_group_created", target=trip_id, detail={"chat_id": chat_id, "members": len(member_ids)})
            return _ok({"trip_id": trip_id, "chat_id": chat_id, "group_name": group_name, "members": len(member_ids), "message": f"企业微信群「{group_name}」已创建"})
        except RuntimeError as e:
            raise HTTPException(502, detail=f"企业微信 API 错误: {e}")

    @fastapi_app.post("/api/trips/{trip_id}/add-members")
    def add_group_members(trip_id: str, body: dict[str, Any], user=Depends(get_current_user), ctx=Depends(get_ctx)):
        """向企业微信群添加成员。body: {"user_ids": ["userid1","userid2"]}"""
        _require_permission_or_403(user, "notification:write")
        trip = _find_trip(trip_id, ctx)
        if trip is None: raise HTTPException(404, "Trip not found")
        assert_trip_access(user, trip)
        chat_id = str(trip.get("wecom_chat_id", ""))
        if not chat_id: raise HTTPException(400, "该行程尚未创建企业微信群")
        try:
            from app.modules.integration.wecom_api import update_group
            user_ids = body.get("user_ids", [])[:100]
            update_group(chat_id, add_users=user_ids)
            ctx.audit_service.record(operator_id=user["id"], action="wecom_members_added", target=trip_id, detail={"chat_id": chat_id, "added": len(user_ids)})
            return _ok({"trip_id": trip_id, "chat_id": chat_id, "added": len(user_ids), "message": f"已添加 {len(user_ids)} 人"})
        except RuntimeError as e:
            raise HTTPException(502, detail=f"企业微信 API 错误: {e}")

    # ═══ 流程剧本 ═══
    @fastapi_app.get("/api/lifecycle-playbook")
    def lifecycle_playbook(user=Depends(get_current_user), ctx=Depends(get_ctx)):
        items = ctx.store.read_collection("lifecycle_playbook")
        if not items:
            items = [
                {"stage":"pre_trip","time_node":"出发前3天","core_work":"游客沟通+行程单处理","action_detail":"1. 确认航班；2. 发送提示；3. 推送行程单给司导","sort_order":10},
                {"stage":"pre_trip","time_node":"出发前","core_work":"资源&物资确认","action_detail":"1. 确认酒店；2. 确定用车；3. 核查物资","sort_order":20},
                {"stage":"pre_trip","time_node":"出发前1天","core_work":"保险核查+群聊搭建","action_detail":"1. 检查保险；2. 建群；3. 司导交底+入群欢迎","sort_order":30},
                {"stage":"in_trip","time_node":"落地当日","core_work":"本地指引+通用提示","action_detail":"1. 推荐景点；2. 发送通用提示","sort_order":40},
                {"stage":"in_trip","time_node":"每日固定时段","core_work":"时段性温馨提示","action_detail":"早/中/晚按季节发送提示","sort_order":50},
                {"stage":"in_trip","time_node":"特殊场景","core_work":"专项安全提示","action_detail":"骑马/滑雪/特殊地区提示","sort_order":60},
                {"stage":"in_trip","time_node":"全程","core_work":"三方协调","action_detail":"协调游客/司导/旅行社问题","sort_order":70},
                {"stage":"post_trip","time_node":"下团即时","core_work":"欢送+满意度调研","action_detail":"1. 发欢送词；2. 满意度调查","sort_order":80},
                {"stage":"post_trip","time_node":"下团后短期","core_work":"售后跟进+客户存档","action_detail":"1. 售后跟进；2. VIP存档","sort_order":90},
                {"stage":"post_trip","time_node":"售后末期","core_work":"群聊解散","action_detail":"发群解散通知并解散群","sort_order":100},
            ]
        return _ok({"playbook": sorted(items, key=lambda x: int(x.get("sort_order",100))), "total": len(items)})

    @fastapi_app.get("/api/trips/{trip_id}/import-snapshot")
    def get_trip_import_snapshot(
        trip_id: str,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        trip = _find_trip(trip_id, ctx)
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
        trip = _find_trip(trip_id, ctx)
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
        trip = _find_trip(trip_id, ctx)
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

    # ── 高品质游客存档 ────────────────────────────────────────────────────────
    @fastapi_app.post("/api/trips/{trip_id}/guests/{guest_id}/mark-vip")
    def mark_guest_vip(
        trip_id: str,
        guest_id: str,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "trip:write")
        trip = _find_trip(trip_id, ctx)
        if trip is None:
            raise HTTPException(status_code=404, detail="Trip not found")
        assert_trip_access(user, trip)
        guests = list(trip.get("guests") or [])
        updated = False
        for g in guests:
            if str(g.get("id") or g.get("phone") or "") == guest_id:
                g["is_vip"] = True
                g["vip_tagged_by"] = user["id"]
                updated = True
                break
        if not updated:
            raise HTTPException(status_code=404, detail="Guest not found")
        ctx.trip_repository.update(trip_id, {"guests": guests})
        ctx.audit_service.record(
            operator_id=user["id"],
            action="guest_marked_vip",
            target=trip_id,
            detail={"guest_id": guest_id},
        )
        return _ok({"trip_id": trip_id, "guest_id": guest_id, "is_vip": True})

    @fastapi_app.get("/api/guests/vip")
    def list_vip_guests(
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "trip:read")
        tenant_id = _current_tenant_id(user)
        vip_list: list[dict[str, Any]] = []
        for trip in ctx.trip_repository.list():
            if str(trip.get("tenant_id", "")) != tenant_id:
                continue
            for g in (trip.get("guests") or []):
                if g.get("is_vip"):
                    vip_list.append({
                        "trip_id": trip.get("id"),
                        "trip_name": trip.get("destination") or trip.get("team_id"),
                        "guest_name": g.get("name"),
                        "guest_phone": g.get("phone"),
                        "vip_tagged_by": g.get("vip_tagged_by"),
                    })
        return _ok({"vip_guests": vip_list, "total": len(vip_list)})

    # ═══ 游客管理 ═══

    @fastapi_app.get("/api/guests")
    def list_guests(
        is_vip: bool | None = None,
        search: str | None = None,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        """列出所有行程中的游客，按手机号去重合并。"""
        _require_permission_or_403(user, "trip:read")
        tenant_id = _current_tenant_id(user)
        # Collect guests from all trips, deduplicate by phone
        seen: set[str] = set()
        guests: list[dict[str, Any]] = []
        for trip in ctx.trip_repository.list():
            if str(trip.get("tenant_id", "")) != tenant_id:
                continue
            for idx, g in enumerate(trip.get("guests") or []):
                phone = str(g.get("phone", "")).strip()
                # Use trip_id + index as unique guest id
                guest_id = f"{trip.get('id', '')}-{idx}"
                if guest_id in seen:
                    continue
                seen.add(guest_id)
                if is_vip and not g.get("is_vip"):
                    continue
                if search:
                    s = search.strip().lower()
                    if s not in str(g.get("name", "")).lower() and s not in phone:
                        continue
                guests.append({
                    "id": guest_id,
                    "name": str(g.get("name", "")),
                    "phone": phone,
                    "is_vip": bool(g.get("is_vip")),
                    "vip_tagged_at": str(g.get("vip_tagged_at") or ""),
                    "trip_id": str(trip.get("id", "")),
                    "trip_name": str(trip.get("destination") or ""),
                })
        return _ok({"guests": guests, "total": len(guests)})

    @fastapi_app.put("/api/guests/{guest_id}")
    def update_guest(
        guest_id: str,
        body: dict[str, Any],
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        """更新游客信息（姓名/电话），同步到所有关联行程。"""
        _require_permission_or_403(user, "trip:write")
        tenant_id = _current_tenant_id(user)
        name = str(body.get("name", "")).strip()
        phone = str(body.get("phone", "")).strip()
        updated_trips = 0
        for trip in ctx.trip_repository.list():
            if str(trip.get("tenant_id", "")) != tenant_id:
                continue
            guests = list(trip.get("guests") or [])
            changed = False
            for idx, g in enumerate(guests):
                gid = f"{trip.get('id', '')}-{idx}"
                if gid == guest_id:
                    if name:
                        g["name"] = name
                        changed = True
                    if phone:
                        g["phone"] = phone
                        changed = True
                    break
            if changed:
                ctx.trip_repository.update(str(trip.get("id", "")), {"guests": guests})
                updated_trips += 1
        if updated_trips == 0:
            raise HTTPException(404, "Guest not found")
        return _ok({"guest": {"id": guest_id, "name": name, "phone": phone}, "updated_trips": updated_trips, "message": "游客信息已更新"})

    @fastapi_app.delete("/api/guests/{guest_id}")
    def delete_guest(
        guest_id: str,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        """从所有关联行程中移除游客。"""
        _require_permission_or_403(user, "trip:write")
        tenant_id = _current_tenant_id(user)
        unlinked = 0
        for trip in ctx.trip_repository.list():
            if str(trip.get("tenant_id", "")) != tenant_id:
                continue
            guests = list(trip.get("guests") or [])
            new_guests = []
            removed = False
            for idx, g in enumerate(guests):
                gid = f"{trip.get('id', '')}-{idx}"
                if gid == guest_id:
                    removed = True
                else:
                    new_guests.append(g)
            if removed:
                ctx.trip_repository.update(str(trip.get("id", "")), {"guests": new_guests})
                unlinked += 1
        if unlinked == 0:
            raise HTTPException(404, "Guest not found")
        return _ok({"deleted": True, "unlinked_trips": unlinked, "message": f"已从 {unlinked} 个行程中移除"})

    # ── 行程单推送给司导 ──────────────────────────────────────────────────────
    # ── 工作流辅助函数 ──────────────────────────────────────────────────
    def _append_notification_attempt(ctx: AppContext, record: dict[str, Any]) -> None:
        """Append a notification attempt record to the store for analytics."""
        existing = ctx.notification_attempt_repository.list_history(limit=None)
        existing.insert(0, record)
        ctx.store.write_collection("notification_attempts", existing)

    def _send_workflow_template(trip, template_key, *, ctx, preview=False, extra=""):
        from app.modules.notification.concierge_playbook import MESSAGE_TEMPLATES
        tpl = MESSAGE_TEMPLATES.get(template_key, "")
        if not tpl: raise HTTPException(status_code=500, detail=f"Template not found: {template_key}")
        vars_ = {"customer_name":trip.get("destination","贵宾"),"destination":trip.get("destination",""),
                 "manager_name":trip.get("trip_manager_name") or trip.get("concierge_name","负责人"),
                 "concierge_name":trip.get("concierge_name","管家"),"driver_name":trip.get("driver_name","司机")}
        for k,v in vars_.items(): tpl = tpl.replace("{{"+k+"}}", str(v))
        from zoneinfo import ZoneInfo
        tpl = f"【{datetime.now(tz=ZoneInfo('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')}】\n{tpl}"
        if preview: return True, tpl
        provider = get_wechat_provider_for_trip(trip)
        ok, msg = provider.send(f"wf:{template_key}:{trip.get('id','')}", tpl)
        # Record notification attempt for analytics
        now_iso = datetime.now(UTC).isoformat()
        attempt_record = {
            "attempt_id": f"wf-{uuid4().hex[:12]}",
            "task_id": f"wf-{template_key}",
            "tenant_id": str(trip.get("tenant_id", "")),
            "trip_id": str(trip.get("id", "")),
            "team_id": str(trip.get("team_id") or trip.get("team", "")),
            "customer_id": "",
            "attempt_no": 1,
            "channel": "wechat_work_group",
            "status": "sent" if ok else "failed",
            "ok": ok,
            "reason": "" if ok else msg,
            "provider_message": msg,
            "latency_ms": 0,
            "attempted_at": now_iso,
        }
        _append_notification_attempt(ctx, attempt_record)
        return ok, msg

    def _update_workflow_status(trip, step, *, ctx, operator_id="", detail=None):
        repo = WorkflowExecutionRepository(store=ctx.store)
        repo.mark(str(trip.get("id","")), step, operator_id=operator_id, detail=detail or {})

    @fastapi_app.post("/api/trips/{trip_id}/notify-driver")
    def notify_driver(
        trip_id: str,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        _require_permission_or_403(user, "notification:write")
        trip = _find_trip(trip_id, ctx)
        if trip is None:
            raise HTTPException(status_code=404, detail="Trip not found")
        assert_trip_access(user, trip)
        driver_name = str(trip.get("driver_name") or "司机")
        driver_phone = str(trip.get("driver_phone") or "")
        destination = str(trip.get("destination") or "")
        start_date = str(trip.get("start_date") or "")
        end_date = str(trip.get("end_date") or "")
        guests = trip.get("guests") or []
        guest_count = len(guests)
        itinerary = trip.get("itinerary") or []
        itinerary_text = "\n".join(
            f"  Day{i+1}: {day.get('title','') or day.get('location','') or ''}"
            for i, day in enumerate(itinerary[:7])
        ) or "  请参见行程详情"
        content = (
            f"【行程确认单】{driver_name}师傅您好！\n"
            f"目的地：{destination}\n"
            f"行程日期：{start_date} ~ {end_date}\n"
            f"游客人数：{guest_count} 人\n"
            f"行程简介：\n{itinerary_text}\n"
            f"负责人：{str(trip.get('trip_manager_name') or trip.get('concierge_name') or '管家')}"
            f"（{str(trip.get('contact_phone') or '')}）\n"
            f"请提前检查车辆，准时就位，谢谢！"
        )
        webhook = get_wechat_provider_for_trip(trip)
        ok, msg = webhook.send(f"driver:{trip_id}", content)
        ctx.audit_service.record(
            operator_id=user["id"],
            action="driver_notified",
            target=trip_id,
            detail={"ok": ok, "driver_name": driver_name, "driver_phone": driver_phone},
        )
        if not ok:
            raise HTTPException(status_code=502, detail=f"WeChat push failed: {msg}")
        return _ok({"trip_id": trip_id, "driver_name": driver_name, "message": "行程单已推送"})

    # ═══ 统一工作流执行 ═══
    @fastapi_app.post("/api/trips/{trip_id}/workflow/execute")
    def execute_workflow(
        trip_id: str,
        step: str = "pre_flight_notice",
        preview: bool = False,
        body: dict[str, Any] | None = None,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        """统一工作流入口。step=pre_flight_notice|resources_verified|insurance_verified|group_built|day1_guide_sent|farewell_sent|survey_sent|group_dismissed|trigger_scheduler"""
        _require_permission_or_403(user, "notification:write")
        trip = _find_trip(trip_id, ctx)
        if trip is None: raise HTTPException(status_code=404, detail="Trip not found")
        assert_trip_access(user, trip)
        VALID = {"pre_flight_notice","resources_verified","insurance_verified","group_built","day1_guide_sent","farewell_sent","survey_sent","group_dismissed","trigger_scheduler","daily_reminder","scene_alert","issue_coordination","follow_up"}
        if step not in VALID: raise HTTPException(status_code=400, detail=f"Invalid step: {step}")
        if step == "trigger_scheduler":
            slot = (body or {}).get("time_slot","morning")
            if hasattr(ctx,"scheduler_service") and ctx.scheduler_service is not None:
                import asyncio; asyncio.ensure_future(ctx.scheduler_service.check_and_send_notifications_for_slot(slot))
            ctx.audit_service.record(operator_id=user["id"],action="scheduler_triggered",target=trip_id)
            return _ok({"trip_id":trip_id,"step":step,"message":f"已触发{slot}调度"})
        if step in ("resources_verified","insurance_verified"):
            tpl_key = "resources_verified_notice" if step == "resources_verified" else "insurance_verified_notice"
            ok,msg = _send_workflow_template(trip,tpl_key,ctx=ctx,preview=preview)
            if preview: return _ok({"trip_id":trip_id,"step":step,"preview":True,"rendered_content":msg})
            if not ok: raise HTTPException(status_code=502,detail=f"推送失败:{msg}")
            _update_workflow_status(trip,step,ctx=ctx,operator_id=user["id"],detail=body or {})
            ctx.audit_service.record(operator_id=user["id"],action=step,target=trip_id)
            return _ok({"trip_id":trip_id,"step":step,"message":"已完成"})
        # day1_guide_sent 需要发送2条消息
        if step == "day1_guide_sent":
            u_ok,u_msg = _send_workflow_template(trip,"urumqi_day1_recommendations",ctx=ctx,preview=preview)
            t_ok,t_msg = _send_workflow_template(trip,"xinjiang_general_tips",ctx=ctx,preview=preview)
            if preview: return _ok({"trip_id":trip_id,"step":step,"preview":True,"rendered_content":f"{u_msg}\n\n---\n\n{t_msg}"})
            if not (u_ok and t_ok): raise HTTPException(status_code=502,detail="推送失败")
            _update_workflow_status(trip,step,ctx=ctx,operator_id=user["id"])
            ctx.audit_service.record(operator_id=user["id"],action=step,target=trip_id)
            return _ok({"trip_id":trip_id,"step":step,"message":"落地首日指引已发送"})

        tpls = {"pre_flight_notice":"pre_flight_notice","farewell_sent":"farewell_message","survey_sent":"post_trip_survey_notice","group_dismissed":"group_close_message","group_built":"group_welcome","resources_verified":"resources_verified_notice","insurance_verified":"insurance_verified_notice","daily_reminder":"daily_reminder_generic","scene_alert":"scene_alert_generic","issue_coordination":"issue_coordination_notice","follow_up":"follow_up_notice"}
        tpl_key = tpls.get(step,step)
        ok,msg = _send_workflow_template(trip,tpl_key,ctx=ctx,preview=preview)
        if preview: return _ok({"trip_id":trip_id,"step":step,"preview":True,"rendered_content":msg})
        if not ok: raise HTTPException(status_code=502,detail=f"推送失败:{msg}")
        _update_workflow_status(trip,step,ctx=ctx,operator_id=user["id"])
        ctx.audit_service.record(operator_id=user["id"],action=step,target=trip_id)
        return _ok({"trip_id":trip_id,"step":step,"message":"已发送"})

    # ── 辅助：按 id 或 team_id 查找行程 ──
    def _find_trip(trip_id: str, ctx) -> dict | None:
        trip = ctx.trip_repository.get(trip_id)
        if trip is None:
            for t in ctx.trip_repository.list():
                if str(t.get("team_id") or t.get("team") or "") == trip_id:
                    return t
        return trip

    # ═══ 工作流状态总览 ═══
    @fastapi_app.get("/api/trips/{trip_id}/workflow-status")
    def workflow_status(trip_id: str, user=Depends(get_current_user), ctx=Depends(get_ctx)):
        _require_permission_or_403(user, "trip:read")
        trip = _find_trip(trip_id, ctx)
        if trip is None: raise HTTPException(404, "Trip not found")
        assert_trip_access(user, trip)
        now = datetime.now(tz=UTC).date()
        sd = str(trip.get("start_date","")); ed = str(trip.get("end_date",""))
        stage = "unknown"
        if sd:
            ts = datetime.strptime(sd,"%Y-%m-%d").date()
            if (ts-now).days>1: stage="pre_trip"
            elif (ts-now).days>=0: stage="in_trip"
        if ed and stage!="pre_trip":
            te = datetime.strptime(ed,"%Y-%m-%d").date()
            if (now-te).days>=0: stage="post_trip"
        steps = [
            {"key":"pre_flight_notice","label":"发送行前提示","time_node":"出发前3天","stage":"pre_trip"},
            {"key":"resources_verified","label":"资源核验确认","time_node":"出发前","stage":"pre_trip"},
            {"key":"insurance_verified","label":"保险核查确认","time_node":"出发前1天","stage":"pre_trip"},
            {"key":"group_built","label":"建群&司导交底","time_node":"出发前1天","stage":"pre_trip"},
            {"key":"day1_guide_sent","label":"落地首日指引","time_node":"落地当日","stage":"in_trip"},
            {"key":"farewell_sent","label":"发送欢送词","time_node":"下团即时","stage":"post_trip"},
            {"key":"survey_sent","label":"发送满意度调研","time_node":"下团即时","stage":"post_trip"},
            {"key":"group_dismissed","label":"群解散通知","time_node":"售后末期","stage":"post_trip"},
        ]
        wf_repo = WorkflowExecutionRepository(store=ctx.store)
        status_map = wf_repo.get_status_map(trip_id)
        for s in steps:
            st = status_map.get(s["key"])
            s["completed"] = bool(st.get("completed")) if st else False
            s["completed_at"] = st.get("completed_at") if st else None
        result = {"pre_trip":[],"in_trip":[],"post_trip":[]}
        for s in steps: result[s["stage"]].append(s)
        done = sum(1 for s in steps if s["completed"])
        return _ok({"trip_id":trip_id,"current_stage":stage,"start_date":sd,"end_date":ed,
                     "progress":{"completed":done,"total":len(steps)},
                     "pre_trip":result["pre_trip"],"in_trip":result["in_trip"],"post_trip":result["post_trip"]})

    # ═══ 游客 & 行程表 & 人员配置 API ═══

    @fastapi_app.get("/api/trips/{trip_id}/guests")
    def list_trip_guests(trip_id: str, user=Depends(get_current_user), ctx=Depends(get_ctx)):
        _require_permission_or_403(user, "trip:read")
        trip = _find_trip(trip_id, ctx)
        if trip is None: raise HTTPException(404, "Trip not found")
        assert_trip_access(user, trip)
        guests = trip.get("guests", [])
        return _ok({"trip_id": trip_id, "guests": guests, "total": len(guests)})

    @fastapi_app.post("/api/trips/{trip_id}/guests")
    def add_trip_guest(trip_id: str, body: dict[str, Any], user=Depends(get_current_user), ctx=Depends(get_ctx)):
        _require_permission_or_403(user, "trip:write")
        trip = _find_trip(trip_id, ctx)
        if trip is None: raise HTTPException(404, "Trip not found")
        assert_trip_access(user, trip)
        guests = list(trip.get("guests", []))
        new_guest = {"name": str(body.get("name","")), "phone": str(body.get("phone","")), "notes": str(body.get("notes",""))}
        guests.append(new_guest)
        ctx.trip_repository.update(str(trip.get("id","")), {"guests": guests})
        ctx.audit_service.record(operator_id=user["id"], action="guest_added", target=trip_id, detail={"name": new_guest["name"]})
        return _ok({"trip_id": trip_id, "guest": new_guest, "message": "游客已添加"})

    @fastapi_app.delete("/api/trips/{trip_id}/guests/{guest_index}")
    def remove_trip_guest(trip_id: str, guest_index: int, user=Depends(get_current_user), ctx=Depends(get_ctx)):
        _require_permission_or_403(user, "trip:write")
        trip = _find_trip(trip_id, ctx)
        if trip is None: raise HTTPException(404, "Trip not found")
        assert_trip_access(user, trip)
        guests = list(trip.get("guests", []))
        if guest_index < 0 or guest_index >= len(guests):
            raise HTTPException(400, "Invalid guest index")
        removed = guests.pop(guest_index)
        ctx.trip_repository.update(str(trip.get("id","")), {"guests": guests})
        return _ok({"trip_id": trip_id, "removed": removed, "message": "游客已移除"})

    @fastapi_app.get("/api/trips/{trip_id}/staff")
    def get_trip_staff(trip_id: str, user=Depends(get_current_user), ctx=Depends(get_ctx)):
        _require_permission_or_403(user, "trip:read")
        trip = _find_trip(trip_id, ctx)
        if trip is None: raise HTTPException(404, "Trip not found")
        assert_trip_access(user, trip)
        staff = [
            {"role": "manager", "name": trip.get("trip_manager_name", ""), "phone": trip.get("trip_manager_phone", "")},
            {"role": "concierge", "name": trip.get("concierge_name", ""), "phone": trip.get("concierge_phone", "")},
            {"role": "driver", "name": trip.get("driver_name", ""), "phone": trip.get("driver_phone", "")},
        ]
        return _ok({"trip_id": trip_id, "staff": staff})

    @fastapi_app.put("/api/trips/{trip_id}/staff")
    def update_trip_staff(trip_id: str, body: dict[str, Any], user=Depends(get_current_user), ctx=Depends(get_ctx)):
        _require_permission_or_403(user, "trip:write")
        trip = _find_trip(trip_id, ctx)
        if trip is None: raise HTTPException(404, "Trip not found")
        assert_trip_access(user, trip)
        staff_list: list[dict[str, str]] = body.get("staff", [])
        role_field_map = {
            "manager": ("trip_manager_name", "trip_manager_phone"),
            "concierge": ("concierge_name", "concierge_phone"),
            "driver": ("driver_name", "driver_phone"),
        }
        updates: dict[str, str] = {}
        for item in staff_list:
            role = str(item.get("role", "")).strip()
            if role not in role_field_map:
                continue
            name_field, phone_field = role_field_map[role]
            updates[name_field] = str(item.get("name", "")).strip()
            updates[phone_field] = str(item.get("phone", "")).strip()
        ctx.trip_repository.update(str(trip.get("id", "")), updates)
        ctx.audit_service.record(operator_id=user["id"], action="staff_updated", target=trip_id, detail={"roles": list(updates.keys())})
        return _ok({"trip_id": trip_id, "staff": staff_list, "message": "人员配置已保存"})

    @fastapi_app.get("/api/trips/{trip_id}/itinerary")
    def get_trip_itinerary(trip_id: str, user=Depends(get_current_user), ctx=Depends(get_ctx)):
        _require_permission_or_403(user, "trip:read")
        trip = _find_trip(trip_id, ctx)
        if trip is None: raise HTTPException(404, "Trip not found")
        assert_trip_access(user, trip)
        days = trip.get("itinerary", [])
        return _ok({"trip_id": trip_id, "days": days, "total": len(days)})

    @fastapi_app.put("/api/trips/{trip_id}/itinerary")
    def update_trip_itinerary(trip_id: str, body: dict[str, Any], user=Depends(get_current_user), ctx=Depends(get_ctx)):
        _require_permission_or_403(user, "trip:write")
        trip = _find_trip(trip_id, ctx)
        if trip is None: raise HTTPException(404, "Trip not found")
        assert_trip_access(user, trip)
        days = body.get("days", [])
        ctx.trip_repository.update(str(trip.get("id","")), {"itinerary": days})
        ctx.audit_service.record(operator_id=user["id"], action="itinerary_updated", target=trip_id, detail={"days": len(days)})
        return _ok({"trip_id": trip_id, "days": days, "message": f"行程表已更新，共 {len(days)} 天"})

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
        trip = _find_trip(trip_id, ctx)
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
            recent = ctx.notification_attempt_repository.get_recent_items(tenant_id=tenant_id, limit=limit)
        return _ok({"total": len(recent), "items": recent})

    @fastapi_app.get("/api/trips/{trip_id}/timeline")
    def trip_timeline(
        trip_id: str,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        trip = _find_trip(trip_id, ctx)
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

    @fastapi_app.get("/api/admin/tenant-notification-config")
    def get_tenant_notification_config(
        user: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        tenant_id = _current_tenant_id(user)
        config = ctx.tenant_notification_config_repository.get(tenant_id) or {
            "tenant_id": tenant_id
        }
        return _ok({"tenant_id": tenant_id, "config": config})

    @fastapi_app.put("/api/admin/tenant-notification-config")
    def upsert_tenant_notification_config(
        payload: TenantNotificationConfigUpsertRequest,
        user: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        tenant_id = _current_tenant_id(user)
        config = ctx.tenant_notification_config_repository.upsert(
            {
                "tenant_id": tenant_id,
                "wechat_webhook_url": payload.wechat_webhook_url,
                "sms_provider": payload.sms_provider,
                "sms_sign_name": payload.sms_sign_name,
                "sms_template_code": payload.sms_template_code,
                "sms_credential_id": payload.sms_credential_id,
            }
        )
        ctx.audit_service.record(
            operator_id=user["id"],
            action="tenant_notification_config_updated",
            target=tenant_id,
            detail={
                "sms_provider": payload.sms_provider,
                "sms_sign_name": payload.sms_sign_name,
                "sms_credential_id": payload.sms_credential_id,
                "wechat_webhook_configured": bool(payload.wechat_webhook_url),
            },
        )
        return _ok({"tenant_id": tenant_id, "config": config})

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
        tenant_id = _current_tenant_id(user)
        active_trips = [
            trip
            for trip in ctx.trip_repository.list(tenant_id=tenant_id)
            if trip.get("status") == "in_progress"
        ]
        triggered_count = 0

        for trip in active_trips:
            project_id = str(
                trip.get("project_id") or trip.get("team_id") or trip.get("team") or ""
            )
            project_config = ctx.project_notification_config_repository.get(
                project_id,
                tenant_id=tenant_id,
            )
            weather_context = dict(project_config or {})
            weather_context.update(trip)
            info = ctx.weather_provider.get_weather(
                str(trip.get("destination", "")),
                location_context=weather_context,
            )
            if not info.warning_level:
                continue

            rendered = (
                f"【天气预警】您在 {info.destination} 的行程受 {info.condition} 影响，"
                f"当前气温 {info.temperature}C，请注意安全。"
            )
            recipients: list[tuple[str, str]] = []
            for guest in trip.get("guests") or []:
                phone = str(guest.get("phone") or "").strip()
                if phone:
                    recipients.append((phone, str(guest.get("name") or "贵宾")))
            if not recipients:
                for field in ("trip_manager_phone", "concierge_phone", "contact_phone"):
                    phone = str(trip.get(field) or "").strip()
                    if phone:
                        recipients.append((phone, "值班管家"))
                        break

            for phone, customer_name in recipients:
                task = NotificationTask(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    team_id=str(trip.get("team_id", "")),
                    trip_id=str(trip.get("id", "")),
                    customer_id=phone,
                    rendered_content=rendered,
                    idempotency_key=(
                        f"weather:{tenant_id}:{trip.get('id')}:{phone}:"
                        f"{datetime.now(tz=UTC).date().isoformat()}"
                    ),
                    notification_type=NotificationType.RISK_ALERT,
                    primary_channel=Channel.SMS,
                    fallback_channel=Channel.WECHAT_WORK_GROUP,
                    provider_context={
                        "customer_name": customer_name,
                        "trip_label": str(trip.get("destination") or trip.get("id", "")),
                        "webhook_url": str(trip.get("webhook_url") or ""),
                    },
                )
                ctx.notification_tasks[task.id] = task
                result = ctx.notification_service.dispatch(task)
                if result.get("ok") and result.get("reason") != "idempotent_skip":
                    triggered_count += 1

        ctx.audit_service.record(
            operator_id=user["id"],
            action="weather_check_triggered",
            target="",
            detail={
                "tenant_id": tenant_id,
                "active_trips_checked": len(active_trips),
                "triggered_notifications": triggered_count,
            },
        )
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

    # ── Notification Rules CRUD ─────────────────────

    @fastapi_app.get("/api/notifications/rules")
    def list_notification_rules(
        enabled: bool | None = None,
        stage: str | None = None,
        time_slot: str | None = None,
        scene: str | None = None,
        trip_id: str | None = None,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        rules = ctx.notification_rule_repository.list_rules(
            tenant_id=_current_tenant_id(user),
            enabled=enabled,
            stage=stage,
            time_slot=time_slot,
            scene=scene,
            trip_id=trip_id,
        )
        return _ok({"total": len(rules), "items": rules})

    @fastapi_app.post("/api/notifications/rules", status_code=201)
    def create_notification_rule(
        payload: NotificationRuleCreateRequest,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        try:
            rule = ctx.notification_rule_repository.create_rule({
                "name": payload.name,
                "stage": payload.stage,
                "time_slot": payload.time_slot,
                "scene": payload.scene,
                "channels": payload.channels,
                "template_id": payload.template_id,
                "enabled": payload.enabled,
                "priority": payload.priority,
                "conditions": payload.conditions,
                "tenant_id": _current_tenant_id(user),
            })
        except RuleValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        return _ok({"rule": rule})

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
        return _ok(rule)

    @fastapi_app.put("/api/notifications/rules/{rule_id}")
    def update_notification_rule(
        rule_id: str,
        payload: NotificationRuleUpdateRequest,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        try:
            rule = ctx.notification_rule_repository.update_rule(
                rule_id,
                payload.model_dump(exclude_none=True),
                tenant_id=_current_tenant_id(user),
            )
        except RuleValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        if rule is None:
            raise HTTPException(status_code=404, detail="Rule not found")
        return _ok(rule)

    @fastapi_app.delete("/api/notifications/rules/{rule_id}")
    def delete_notification_rule(
        rule_id: str,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        deleted = ctx.notification_rule_repository.delete_rule(
            rule_id, tenant_id=_current_tenant_id(user)
        )
        if not deleted:
            raise HTTPException(status_code=404, detail="Rule not found")
        return _ok({"deleted": True})

    return fastapi_app


_APP: FastAPI | None = None


def get_app() -> FastAPI:
    """Create the ASGI app lazily so importing this module has no DB side effects."""
    global _APP
    if _APP is None:
        _APP = create_app()
    return _APP


def __getattr__(name: str) -> Any:
    # Preserve ``uvicorn app.api.http:app`` while keeping import side-effect free.
    if name == "app":
        return get_app()
    raise AttributeError(name)


def reset_state(purge_persistence: bool = False) -> None:
    store = JsonFileStore()
    if purge_persistence:
        store.clear_all()
    get_app().state.ctx = _build_context(store=store)


def dispatch_request(
    method: str, path: str, headers: dict[str, str] | None = None, body: str = ""
) -> Response:
    from fastapi.testclient import TestClient

    client = TestClient(get_app())
    response = client.request(method, path, headers=headers or {}, data=body)
    payload: dict[str, Any]
    if response.content:
        payload = response.json()
    else:
        payload = {"code": response.status_code}
    return Response(status=response.status_code, body=payload)


def run_http_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    uvicorn.run(get_app(), host=host, port=port)
