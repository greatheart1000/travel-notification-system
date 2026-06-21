from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

UTC = timezone.utc


@dataclass(slots=True)
class BaseRecord:
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))


@dataclass(slots=True)
class DomainEvent(BaseRecord):
    event_type: str = "itinerary_updated"
    team_id: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class NotificationAttempt:
    id: str = field(default_factory=lambda: str(uuid4()))
    task_id: str = ""
    attempt_no: int = 1
    channel: str = "sms"
    ok: bool = False
    reason: str = ""
    provider_message: str = ""
    latency_ms: int = 0
    attempted_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
