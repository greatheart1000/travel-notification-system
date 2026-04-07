from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class Channel(str, Enum):
    SMS = "sms"
    WECHAT_WORK_GROUP = "wechat_work_group"


class NotificationType(str, Enum):
    BOOKING_SUCCESS = "booking_success"
    PRE_TRIP_REMINDER = "pre_trip_reminder"
    DAILY_REMINDER = "daily_reminder"
    RISK_ALERT = "risk_alert"
    FAREWELL = "farewell"
    SATISFACTION = "satisfaction"
    COMPLAINT_ESCALATION = "complaint_escalation"


class EventType(str, Enum):
    ITINERARY_UPDATED = "itinerary_updated"
    WEATHER_RISK_TRIGGERED = "weather_risk_triggered"
    COMPLAINT_DETECTED = "complaint_detected"
    SURVEY_LOW_SCORE = "survey_low_score"


@dataclass(slots=True)
class BaseRecord:
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))


@dataclass(slots=True)
class DomainEvent(BaseRecord):
    event_type: EventType = EventType.ITINERARY_UPDATED
    team_id: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
