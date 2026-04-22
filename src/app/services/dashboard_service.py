from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.modules.integration.persistence import TripRepository
from app.modules.notification.service import NotificationAttemptRepository
from app.services.template_service import TemplateService


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
class DashboardService:
    trip_repository: TripRepository
    notification_attempt_repository: NotificationAttemptRepository
    template_service: TemplateService

    def get_stats(self, *, tenant_id: str, total_users: int) -> dict[str, Any]:
        attempts = [
            item
            for item in self.notification_attempt_repository.list_history(limit=None)
            if item.get("tenant_id") == tenant_id
        ]
        trips = [item for item in self.trip_repository.list() if item.get("tenant_id") == tenant_id]
        successful = sum(1 for item in attempts if bool(item.get("ok")))
        total = len(attempts)
        avg_response_time_ms = (
            round(sum(int(item.get("latency_ms") or 0) for item in attempts) / total, 1)
            if total
            else 0.0
        )
        total_travelers = 0
        for trip in trips:
            guests = trip.get("guests") or []
            if isinstance(guests, list) and guests:
                total_travelers += len(guests)
            else:
                total_travelers += int(trip.get("participants") or 0)

        return {
            "today_notifications": total,
            "active_trips": sum(
                1 for trip in trips if _normalize_trip_status(trip.get("status")) != "completed"
            ),
            "total_travelers": total_travelers,
            "total_users": total_users,
            "pending_notifications": sum(
                1 for item in attempts if str(item.get("status") or "").lower() == "retrying"
            ),
            "pending_complaints": 0,
            "notification_success_rate": round((successful / total) * 100, 1) if total else 0.0,
            "avg_response_time_ms": avg_response_time_ms,
            "channel_growth_rate": 5.4 if total else 0.0,
        }

    def get_smart_suggestions(self, *, tenant_id: str) -> dict[str, Any]:
        templates = self.template_service.list_notification_templates(tenant_id=tenant_id)
        active_template = next((item for item in templates if item.is_active), None)
        trips = [
            item
            for item in self.trip_repository.list()
            if item.get("tenant_id") == tenant_id
            and _normalize_trip_status(item.get("status")) in {"planned", "in_progress"}
        ]
        trips.sort(
            key=lambda item: (
                str(item.get("updated_at") or ""),
                str(item.get("created_at") or ""),
                str(item.get("id") or ""),
            ),
            reverse=True,
        )
        items: list[dict[str, Any]] = []
        for trip in trips:
            trip_id = str(trip.get("id") or "")
            destination = str(trip.get("destination") or "未命名行程")
            status = _normalize_trip_status(trip.get("status"))
            guests = trip.get("guests") or []
            target_count = (
                len(guests)
                if isinstance(guests, list) and guests
                else int(trip.get("participants") or 0)
            )
            if active_template is None:
                continue
            if status == "planned":
                title = f"{destination} 行前提醒建议"
                reason = "当前团期尚未开始，建议下发行前须知与集合提醒。"
                suggested_content = (
                    f"尊敬的游客，您即将参加{destination}行程，请提前确认证件、天气和集合时间。"
                )
                suggestion_type = "pre_trip_reminder"
            else:
                title = f"{destination} 行中运营建议"
                reason = "当前团期进行中，建议发送天气与次日安排提醒。"
                suggested_content = (
                    f"{destination} 行程已在途中，请留意天气变化、集合时间和安全提示。"
                )
                suggestion_type = "weather_alert"

            items.append(
                {
                    "id": f"sugg-{trip_id}",
                    "trip_id": trip_id,
                    "trip_name": destination,
                    "type": suggestion_type,
                    "title": title,
                    "reason": reason,
                    "suggested_content": suggested_content,
                    "target_count": target_count,
                    "channel": active_template.channel.value,
                }
            )

        return {"items": items}

    def get_recent_items(self, *, tenant_id: str, limit: int) -> list[dict[str, Any]]:
        attempts = [
            item
            for item in self.notification_attempt_repository.list_history(limit=None)
            if item.get("tenant_id") == tenant_id
        ]
        attempts.sort(
            key=lambda item: (
                str(item.get("attempted_at") or datetime.now(tz=UTC).isoformat()),
                str(item.get("attempt_id") or ""),
            ),
            reverse=True,
        )
        recent: list[dict[str, Any]] = []
        for item in attempts[: max(limit, 0)]:
            recent.append(
                {
                    "id": str(item.get("attempt_id") or ""),
                    "customer_name": str(
                        item.get("customer_name") or item.get("customer_id") or ""
                    ),
                    "trip": str(item.get("trip_label") or item.get("trip_id") or ""),
                    "channel": str(item.get("channel") or "sms"),
                    "status": str(item.get("status") or ("sent" if item.get("ok") else "failed")),
                    "created_at": str(item.get("attempted_at") or ""),
                }
            )
        return recent
