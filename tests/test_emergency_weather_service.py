from __future__ import annotations

from typing import Any

from app.modules.integration.weather_provider import WeatherInfo
from app.modules.notification.service import NotificationService
from app.modules.trigger.risk_alert_service import RiskAlertService
from app.services.emergency_weather_service import EmergencyWeatherService
from app.services.template_service import TemplateService
from app.services.weather_alert_ai_service import WeatherAlertAIService


class _TripRepo:
    def __init__(self, items: list[dict[str, Any]]):
        self._items = items

    def list(self) -> list[dict[str, Any]]:
        return self._items


class _ProjectConfigRepo:
    def get(self, project_id: str, tenant_id: str) -> dict[str, Any]:
        return {"project_id": project_id, "tenant_id": tenant_id}


class _WeatherProvider:
    def get_weather(
        self, destination: str, location_context: dict[str, Any] | None = None
    ) -> WeatherInfo:
        return WeatherInfo(
            destination=destination or "九寨沟",
            condition="中雨",
            temperature=11.0,
            warning_level="orange",
            alert_title="暴雨橙色预警",
            source="mock",
        )


def _build_service(trips: list[dict[str, Any]]) -> EmergencyWeatherService:
    return EmergencyWeatherService(
        trip_repository=_TripRepo(trips),
        project_notification_config_repository=_ProjectConfigRepo(),
        weather_provider=_WeatherProvider(),  # type: ignore[arg-type]
        risk_alert_service=RiskAlertService(),
        template_service=TemplateService(),
        notification_service=NotificationService(),
        ai_service=WeatherAlertAIService(),
    )


def test_emergency_weather_summary_contains_closure_fields() -> None:
    service = _build_service(
        [
            {
                "id": "trip-1",
                "tenant_id": "tenant-a",
                "team_id": "TEAM-A",
                "destination": "九寨沟",
                "status": "in_progress",
                "participants": 20,
                "start_date": "2026-04-22",
            },
            {
                "id": "trip-2",
                "tenant_id": "tenant-a",
                "team_id": "TEAM-B",
                "destination": "成都",
                "status": "planned",
                "participants": 16,
                "start_date": "2026-04-23",
            },
        ]
    )

    summary = service.get_summary("tenant-a")

    assert summary["today_weather_summary"]
    assert summary["risk_level_label"] in {"较高", "高危", "中等", "关注"}
    assert summary["affected_region"] == "九寨沟"
    assert summary["affected_trip_count"] == 2
    assert len(summary["affected_trips"]) == 2
    assert summary["ai_risk_analysis"]["affected_trip_ids"] == ["trip-1", "trip-2"]
    assert summary["ai_risk_analysis"]["affected_stage"]
    assert isinstance(summary["ai_risk_analysis"]["recommend_send"], bool)
    assert summary["tourist_notification"]
    assert summary["internal_notification"]
    assert summary["suggested_actions"]
    # backward compatibility
    assert summary["generated_notification"] == summary["tourist_notification"]
    assert summary["requires_confirmation"] is True


def test_emergency_weather_summary_empty_has_stable_copy() -> None:
    service = _build_service([])
    summary = service.get_summary("tenant-a")

    assert summary["affected_trip_count"] == 0
    assert summary["affected_region"] == "暂无"
    assert summary["ai_risk_analysis"]["recommend_send"] is False
    assert summary["tourist_notification"]
    assert summary["internal_notification"]
    assert summary["suggested_actions"] == ["完善团期数据后重试评估"]


def test_emergency_weather_send_uses_custom_content_first() -> None:
    service = _build_service(
        [
            {
                "id": "trip-1",
                "tenant_id": "tenant-a",
                "team_id": "TEAM-A",
                "destination": "九寨沟",
                "status": "in_progress",
                "participants": 20,
                "start_date": "2026-04-22",
            }
        ]
    )

    result = service.send_summary(
        tenant_id="tenant-a",
        operator_id="admin",
        custom_content="【人工确认】请按领队通知调整返程集合时间。",
        channel="sms",
    )

    assert result["ok"] is True
    assert result["sent_count"] >= 1
    assert result["content"] == "【人工确认】请按领队通知调整返程集合时间。"
