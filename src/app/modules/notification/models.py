from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from app.core.models import UTC, BaseRecord, Channel, NotificationType


class DispatchStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    MANUAL_INTERVENTION = "manual_intervention"
    SKIPPED = "skipped"


@dataclass(slots=True)
class NotificationTemplate(BaseRecord):
    name: str = ""
    version: int = 1
    notification_type: NotificationType = NotificationType.DAILY_REMINDER
    channel: Channel = Channel.SMS
    content: str = ""
    is_active: bool = True


@dataclass(slots=True)
class NotificationAttempt(BaseRecord):
    task_id: str = ""
    attempt_no: int = 1
    channel: Channel = Channel.SMS
    ok: bool = False
    reason: str = ""
    provider_message: str = ""
    latency_ms: int = 0
    attempted_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))


@dataclass(slots=True)
class NotificationTask(BaseRecord):
    team_id: str = ""
    trip_id: str = ""
    customer_id: str = ""
    notification_type: NotificationType = NotificationType.DAILY_REMINDER
    primary_channel: Channel = Channel.SMS
    fallback_channel: Channel | None = Channel.WECHAT_WORK_GROUP
    rendered_content: str = ""
    retry_count: int = 0
    max_retry: int = 2
    manual_intervention_required: bool = False
    status: DispatchStatus = DispatchStatus.PENDING
    idempotency_key: str = ""
    attempts: list[NotificationAttempt] = field(default_factory=list)
