from __future__ import annotations

from app.modules.integration.weather_provider import WeatherInfo
from app.modules.notification.service import NotificationService
from app.modules.trigger.risk_alert_service import RiskAlertService
from app.services.emergency_weather_service import EmergencyWeatherService
from app.services.template_service import TemplateService
from app.services.weather_alert_ai_service import WeatherAlertAIService


class _TripRepository:
    def list(self) -> list[dict[str, object]]:
        return [
            {
                "id": "trip-1",
                "tenant_id": "tenant-1",
                "team_id": "team-1",
                "destination": "乌鲁木齐",
                "status": "planned",
                "start_date": "2026-05-13",
                "participants": 24,
            }
        ]


class _ProjectNotificationConfigRepository:
    def get(self, project_id: str, tenant_id: str) -> dict[str, object]:
        return {}


class _WeatherProvider:
    def get_weather(
        self,
        destination: str,
        location_context: dict[str, object] | None = None,
    ) -> WeatherInfo:
        return WeatherInfo(
            destination=destination,
            condition="阴",
            temperature=8.0,
            daily_forecast=[
                {
                    "fx_date": "2026-05-12",
                    "text_day": "中雨",
                    "text_night": "多云",
                    "temp_max": 12.0,
                    "temp_min": 7.0,
                    "wind_scale_day": "3-4",
                    "wind_speed_day": 24.0,
                    "precip": 8.6,
                },
                {
                    "fx_date": "2026-05-13",
                    "text_day": "晴",
                    "text_night": "晴",
                    "temp_max": 13.0,
                    "temp_min": 6.0,
                    "wind_scale_day": "1-3",
                    "wind_speed_day": 3.0,
                    "precip": 0.0,
                },
            ],
            source="qweather",
        )


def test_emergency_weather_summary_uses_daily_forecast() -> None:
    service = EmergencyWeatherService(
        trip_repository=_TripRepository(),
        project_notification_config_repository=_ProjectNotificationConfigRepository(),
        weather_provider=_WeatherProvider(),
        risk_alert_service=RiskAlertService(),
        template_service=TemplateService(),
        notification_service=NotificationService(),
        ai_service=WeatherAlertAIService(),
    )

    summary = service.get_summary("tenant-1")

    assert "未来两天预报" in summary["weather_summary"]
    assert "2026-05-12中雨" in summary["weather_summary"]
    assert "降水8.6mm" in summary["weather_summary"]
    assert "未来两天预报" in summary["generated_notification"]
