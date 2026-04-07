from __future__ import annotations

from dataclasses import dataclass, field

from app.core.models import BaseRecord, NotificationType


@dataclass(slots=True)
class TriggerRule(BaseRecord):
    code: str = ""
    name: str = ""
    notification_type: NotificationType = NotificationType.DAILY_REMINDER
    is_mandatory: bool = False
    source: str = "weather"
    conditions: dict[str, str | int | float] = field(default_factory=dict)
