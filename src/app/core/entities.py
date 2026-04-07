from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4


class EventName(str, Enum):
    TRIP_CREATED = "trip.created"
    FLIGHT_DELAYED = "flight.delayed"
    CHECKIN_OPEN = "checkin.open"
    WEATHER_ALERT = "weather.alert"


class Channel(str, Enum):
    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"


class DeliveryStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"


@dataclass(slots=True)
class User:
    user_id: str
    locale: str = "zh"
    timezone: str = "Asia/Shanghai"


@dataclass(slots=True)
class UserPreference:
    user_id: str
    channels: list[Channel] = field(default_factory=lambda: [Channel.EMAIL, Channel.PUSH])
    quiet_hours: tuple[int, int] = (23, 7)  # start_hour, end_hour
    allow_marketing: bool = True


@dataclass(slots=True)
class Trip:
    trip_id: str
    user_id: str
    destination: str
    starts_at: datetime
    status: str = "active"


@dataclass(slots=True)
class DomainEvent:
    event_id: str
    name: EventName
    trip_id: str
    user_id: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict = field(default_factory=dict)


@dataclass(slots=True)
class Template:
    template_id: str
    event_name: EventName
    locale: str
    version: int
    content: str
    ab_bucket: str = "A"
    enabled: bool = True


@dataclass(slots=True)
class NotificationRecord:
    notification_id: str = field(default_factory=lambda: str(uuid4()))
    event_id: str = ""
    user_id: str = ""
    trip_id: str = ""
    channel: Channel = Channel.EMAIL
    status: DeliveryStatus = DeliveryStatus.PENDING
    attempt: int = 0
    dedupe_key: str = ""
    trace_id: str = field(default_factory=lambda: str(uuid4()))
    provider_response: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
