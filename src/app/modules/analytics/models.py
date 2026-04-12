from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(slots=True)
class AnalyticsNotificationFact:
    """渠道通知事实表（逻辑表：analytics_notification_facts）。"""

    event_id: str
    event_date: date
    trip_id: str
    team_id: str
    channel: str
    success: bool
    latency_ms: int


@dataclass(slots=True)
class AnalyticsTripFeedback:
    """行程满意度事实表（逻辑表：analytics_trip_feedbacks）。"""

    feedback_id: str
    trip_id: str
    score: float
    submitted_on: date


@dataclass(slots=True)
class AnalyticsTripDimension:
    """行程维度表（逻辑表：analytics_trip_dimensions）。"""

    trip_id: str
    trip_name: str
    destination: str
