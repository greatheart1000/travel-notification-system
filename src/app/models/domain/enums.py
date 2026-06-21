from __future__ import annotations

from enum import Enum


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


class TripStatus(str, Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class StaffRole(str, Enum):
    MANAGER = "manager"
    CONCIERGE = "concierge"
    DRIVER = "driver"


class DispatchStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    MANUAL_INTERVENTION = "manual_intervention"
    SKIPPED = "skipped"


class RuleStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    REJECTED = "rejected"


class RiskResponseLevel(str, Enum):
    AUTO_SENT = "auto_sent"
    MANAGER_CONFIRMED = "manager_confirmed"
    MANAGEMENT_ESCALATED = "management_escalated"
