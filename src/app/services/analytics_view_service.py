from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.modules.analytics.service import AnalyticsService
from app.modules.integration.persistence import TripRepository


def _normalize_trip_status(value: Any) -> str:
    raw = str(value or "").strip().lower()
    mapping = {
        "planned": "planned",
        "计划中": "planned",
        "in_progress": "in_progress",
        "进行中": "in_progress",
        "active": "in_progress",
        "completed": "completed",
        "已完成": "completed",
        "cancelled": "cancelled",
        "已取消": "cancelled",
    }
    return mapping.get(raw, "planned")


@dataclass(slots=True)
class AnalyticsViewService:
    analytics_service: AnalyticsService
    trip_repository: TripRepository

    def build_itinerary_rows(self, *, tenant_id: str) -> list[dict[str, Any]]:
        trips = [item for item in self.trip_repository.list() if item.get("tenant_id") == tenant_id]
        trips.sort(
            key=lambda item: (
                0 if _normalize_trip_status(item.get("status")) == "in_progress" else 1,
                str(item.get("start_date") or ""),
                str(item.get("id") or ""),
            )
        )
        rows: list[dict[str, Any]] = []
        for trip in trips:
            itinerary = trip.get("itinerary") or []
            if not isinstance(itinerary, list):
                continue
            for item in itinerary:
                if not isinstance(item, dict):
                    continue
                rows.append(
                    {
                        "date": str(item.get("date") or ""),
                        "transport": str(item.get("transport") or ""),
                        "route": str(item.get("route") or ""),
                        "hotel": str(item.get("hotel") or ""),
                        "trip_id": str(trip.get("id") or ""),
                        "trip_name": str(trip.get("destination") or ""),
                    }
                )
            if rows:
                break

        if rows:
            return rows

        return [
            {
                "date": "2026-04-18",
                "transport": "Transport",
                "route": "Suram Hotel to Climate Parian",
                "hotel": "TEAM-DEMO-ON",
                "trip_id": "seed-itinerary",
                "trip_name": "默认演示行程",
            }
        ]

    def build_metrics_payload(
        self, base_payload: dict[str, Any], *, tenant_id: str
    ) -> dict[str, Any]:
        payload = dict(base_payload)
        payload["itinerary_rows"] = self.build_itinerary_rows(tenant_id=tenant_id)
        return payload
