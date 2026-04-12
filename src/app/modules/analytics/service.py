from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any
from uuid import uuid4

from app.modules.analytics.models import (
    AnalyticsNotificationFact,
    AnalyticsTripDimension,
    AnalyticsTripFeedback,
)
from app.modules.integration.persistence import JsonFileStore, TripRepository
from app.modules.notification.service import NotificationAttemptRepository

UTC = timezone.utc


class AnalyticsRepository:
    """Analytics logical tables backed by JsonFileStore collections."""

    def __init__(self, store: JsonFileStore) -> None:
        self.store = store

    def list_notification_facts(self) -> list[dict[str, Any]]:
        return self.store.read_collection("analytics_notification_facts")

    def list_feedbacks(self) -> list[dict[str, Any]]:
        return self.store.read_collection("analytics_trip_feedbacks")

    def list_trip_dimensions(self) -> list[dict[str, Any]]:
        return self.store.read_collection("analytics_trip_dimensions")

    def write_notification_facts(self, rows: list[dict[str, Any]]) -> None:
        self.store.write_collection("analytics_notification_facts", rows)

    def write_feedbacks(self, rows: list[dict[str, Any]]) -> None:
        self.store.write_collection("analytics_trip_feedbacks", rows)

    def write_trip_dimensions(self, rows: list[dict[str, Any]]) -> None:
        self.store.write_collection("analytics_trip_dimensions", rows)


class AnalyticsService:
    def __init__(
        self,
        repository: AnalyticsRepository,
        attempt_repository: NotificationAttemptRepository,
        trip_repository: TripRepository,
    ) -> None:
        self.repository = repository
        self.attempt_repository = attempt_repository
        self.trip_repository = trip_repository

    def ensure_seed_data(self) -> None:
        if self.repository.list_notification_facts():
            return

        attempts = self.attempt_repository.list_history(limit=500)
        facts: list[dict[str, Any]] = []
        for item in attempts:
            attempted_at = str(item.get("attempted_at") or datetime.now(UTC).isoformat())
            event_date = attempted_at[:10]
            facts.append(
                asdict(
                    AnalyticsNotificationFact(
                        event_id=str(item.get("attempt_id") or uuid4()),
                        event_date=datetime.fromisoformat(event_date).date(),
                        trip_id=str(item.get("trip_id") or ""),
                        team_id=str(item.get("team_id") or ""),
                        channel=str(item.get("channel") or "sms"),
                        success=bool(item.get("ok", False)),
                        latency_ms=int(item.get("latency_ms") or 1200),
                    )
                )
            )

        if not facts:
            now = datetime.now(UTC)
            defaults = [
                ("trip-seed-001", "sms", True, 780),
                ("trip-seed-001", "wechat_work_group", True, 640),
                ("trip-seed-002", "sms", False, 1800),
                ("trip-seed-002", "wechat_work_group", True, 880),
                ("trip-seed-003", "email", True, 1100),
                ("trip-seed-003", "sms", True, 900),
            ]
            for index, (trip_id, channel, success, latency_ms) in enumerate(defaults):
                facts.append(
                    asdict(
                        AnalyticsNotificationFact(
                            event_id=f"evt-seed-{index + 1}",
                            event_date=(now - timedelta(days=index % 7)).date(),
                            trip_id=trip_id,
                            team_id=f"TEAM-{index + 1:03d}",
                            channel=channel,
                            success=success,
                            latency_ms=latency_ms,
                        )
                    )
                )

        self.repository.write_notification_facts(facts)

        if not self.repository.list_trip_dimensions():
            trips = self.trip_repository.list()
            dimensions: list[dict[str, Any]] = []
            for trip in trips:
                trip_id = str(trip.get("id") or "")
                if not trip_id:
                    continue
                dimensions.append(
                    asdict(
                        AnalyticsTripDimension(
                            trip_id=trip_id,
                            trip_name=f"{trip.get('destination', '未命名行程')} ({trip_id[:8]})",
                            destination=str(trip.get("destination") or "未知目的地"),
                        )
                    )
                )
            if not dimensions:
                dimensions = [
                    asdict(
                        AnalyticsTripDimension(
                            trip_id="trip-seed-001",
                            trip_name="阿勒泰5日团",
                            destination="阿勒泰",
                        )
                    ),
                    asdict(
                        AnalyticsTripDimension(
                            trip_id="trip-seed-002",
                            trip_name="成都亲子周末营",
                            destination="成都",
                        )
                    ),
                    asdict(
                        AnalyticsTripDimension(
                            trip_id="trip-seed-003",
                            trip_name="西安历史文化线",
                            destination="西安",
                        )
                    ),
                ]
            self.repository.write_trip_dimensions(dimensions)

        if not self.repository.list_feedbacks():
            feedbacks = [
                asdict(
                    AnalyticsTripFeedback(
                        feedback_id="fb-seed-001",
                        trip_id="trip-seed-001",
                        score=4.8,
                        submitted_on=datetime.now(UTC).date(),
                    )
                ),
                asdict(
                    AnalyticsTripFeedback(
                        feedback_id="fb-seed-002",
                        trip_id="trip-seed-002",
                        score=4.2,
                        submitted_on=datetime.now(UTC).date(),
                    )
                ),
                asdict(
                    AnalyticsTripFeedback(
                        feedback_id="fb-seed-003",
                        trip_id="trip-seed-003",
                        score=4.6,
                        submitted_on=datetime.now(UTC).date(),
                    )
                ),
            ]
            self.repository.write_feedbacks(feedbacks)

    def build_metrics_snapshot(self) -> dict[str, Any]:
        self.ensure_seed_data()

        facts = self.repository.list_notification_facts()
        feedbacks = self.repository.list_feedbacks()
        dimensions = {row.get("trip_id"): row for row in self.repository.list_trip_dimensions()}

        total = len(facts)
        successful = sum(1 for row in facts if bool(row.get("success")))
        failed = total - successful
        success_rate = round((successful / total) * 100, 1) if total else 0.0
        retry_rate = round((failed / total) * 100, 1) if total else 0.0
        avg_latency = round(mean(int(row.get("latency_ms") or 0) for row in facts), 1) if facts else 0.0

        last_7_days = datetime.now(UTC).date() - timedelta(days=7)
        recent = [row for row in facts if str(row.get("event_date", "")) >= str(last_7_days)]
        previous = [
            row
            for row in facts
            if str(last_7_days - timedelta(days=7)) <= str(row.get("event_date", "")) < str(last_7_days)
        ]
        wow_growth = 0.0
        if previous:
            wow_growth = round(((len(recent) - len(previous)) / len(previous)) * 100, 1)

        avg_score = round(mean(float(row.get("score") or 0.0) for row in feedbacks), 1) if feedbacks else 0.0

        by_channel: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in facts:
            by_channel[str(row.get("channel") or "sms")].append(row)

        channel_rows: list[dict[str, Any]] = []
        for channel, rows in sorted(by_channel.items()):
            sent = len(rows)
            ok = sum(1 for item in rows if bool(item.get("success")))
            failed = sent - ok
            rate = round((ok / sent) * 100, 1) if sent else 0.0
            channel_rows.append(
                {
                    "channel": channel,
                    "name": channel,
                    "sent": sent,
                    "successful": ok,
                    "failed": failed,
                    "rate": f"{rate}%",
                    "success_rate": f"{rate}%",
                }
            )

        by_trip: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in facts:
            by_trip[str(row.get("trip_id") or "")].append(row)

        feedback_by_trip: dict[str, list[float]] = defaultdict(list)
        for row in feedbacks:
            feedback_by_trip[str(row.get("trip_id") or "")].append(float(row.get("score") or 0.0))

        trip_rows: list[dict[str, Any]] = []
        for trip_id, rows in by_trip.items():
            if not trip_id:
                continue
            score_values = feedback_by_trip.get(trip_id, [4.5])
            trip_dimension = dimensions.get(trip_id, {})
            trip_rows.append(
                {
                    "name": trip_dimension.get("trip_name") or f"行程 {trip_id[:8]}",
                    "notifications": len(rows),
                    "satisfaction": round(mean(score_values), 1),
                }
            )

        trip_rows.sort(key=lambda item: item["notifications"], reverse=True)

        return {
            "metrics": {
                "notification_success_rate": f"{success_rate}%",
                "notification_retry_rate": f"{retry_rate}%",
                "notification_manual_takeover_rate": "0.0%",
                "rule_publish_lead_time": "0m",
                "cross_tenant_forbidden_count": 0,
                "avg_response_time": f"{avg_latency}ms",
                "wow_growth": f"{wow_growth:+.1f}%",
                "user_satisfaction": f"{avg_score}/5",
            },
            "channel_performance": channel_rows,
            "top_trips": trip_rows[:5],
        }
