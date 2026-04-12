from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.core.models import BaseRecord, NotificationType


@dataclass(slots=True)
class TriggerRule(BaseRecord):
    code: str = ""
    name: str = ""
    notification_type: NotificationType = NotificationType.DAILY_REMINDER
    is_mandatory: bool = False
    enabled: bool = True
    source: str = "weather"
    priority: int = 100
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    conditions: dict[str, Any] = field(default_factory=dict)
