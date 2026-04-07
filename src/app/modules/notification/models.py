from __future__ import annotations

from dataclasses import dataclass, field

from app.core.models import BaseRecord, Channel, NotificationType


@dataclass(slots=True)
class NotificationTemplate(BaseRecord):
    name: str = ""
    version: int = 1
    notification_type: NotificationType = NotificationType.DAILY_REMINDER
    channel: Channel = Channel.SMS
    content: str = ""
    is_active: bool = True


@dataclass(slots=True)
class NotificationTask(BaseRecord):
    team_id: str = ""
    customer_id: str = ""
    notification_type: NotificationType = NotificationType.DAILY_REMINDER
    primary_channel: Channel = Channel.SMS
    fallback_channel: Channel | None = Channel.WECHAT_WORK_GROUP
    rendered_content: str = ""
    retry_count: int = 0
    manual_intervention_required: bool = False
