from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field, field_validator

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


# ── 行程执行流程 API 请求体模型 ────────────────────────────────────────────

class ResourceVerifyRequest(BaseModel):
    hotel_ok: bool = True
    vehicle_ok: bool = True
    equipment_ok: bool = True
    note: str = Field(default="", max_length=500)


class InsuranceVerifyRequest(BaseModel):
    insurance_ok: bool = True
    note: str = Field(default="", max_length=500)


class BuildGroupRequest(BaseModel):
    steps: list[str] = Field(default_factory=lambda: ["driver_brief", "group_welcome", "pre_flight_notice"], max_length=5)

    @field_validator("steps")
    @classmethod
    def check_steps(cls, v: list[str]) -> list[str]:
        valid = {"driver_brief", "group_welcome", "pre_flight_notice"}
        for s in v:
            if s not in valid:
                raise ValueError(f"无效步骤: {s}，可选: {', '.join(sorted(valid))}")
        return v


class GuestCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    phone: str = Field(min_length=7, max_length=20)

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v: str) -> str:
        if not v.strip().replace("+", "").replace("-", "").replace(" ", "").isdigit():
            raise ValueError("电话号码只能包含数字、+、- 和空格")
        return v.strip()


class GuestUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    phone: str | None = Field(default=None, min_length=7, max_length=20)


class StaffBatchRequest(BaseModel):
    staff: list[dict[str, str]] = Field(default_factory=list, min_length=1, max_length=10)

    @field_validator("staff")
    @classmethod
    def check_staff(cls, v: list[dict[str, str]]) -> list[dict[str, str]]:
        valid_roles = {"manager", "concierge", "driver"}
        for s in v:
            if s.get("role") not in valid_roles:
                raise ValueError(f"无效角色: {s.get('role')}，可选: manager, concierge, driver")
            if not s.get("name", "").strip():
                raise ValueError("姓名不能为空")
        return v


class ItineraryDayItem(BaseModel):
    title: str = Field(default="", max_length=128)
    location: str = Field(default="", max_length=128)
    description: str = Field(default="", max_length=2000)


class ItineraryBatchRequest(BaseModel):
    days: list[ItineraryDayItem] = Field(default_factory=list, max_length=90)


class BatchSendWorkflowRequest(BaseModel):
    trip_ids: list[str] = Field(min_length=1, max_length=100)
    template_key: str = Field(min_length=1, max_length=64)


class TriggerSchedulerRequest(BaseModel):
    time_slot: str = "morning"

    @field_validator("time_slot")
    @classmethod
    def check_slot(cls, v: str) -> str:
        if v not in ("morning", "afternoon", "evening"):
            raise ValueError(f"无效时段: {v}，可选: morning, afternoon, evening")
        return v


class WebhookConfigRequest(BaseModel):
    webhook_urls: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("webhook_urls")
    @classmethod
    def check_urls(cls, v: list[str]) -> list[str]:
        for url in v:
            if not url.startswith(("http://", "https://")):
                raise ValueError(f"无效URL: {url}，必须以 http:// 或 https:// 开头")
        return v

