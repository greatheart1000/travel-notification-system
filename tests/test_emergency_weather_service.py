from __future__ import annotations

from typing import Any

from app.modules.integration.weather_provider import WeatherInfo
from app.modules.notification.service import NotificationService
from app.modules.trigger.risk_alert_service import RiskAlertService
from app.services.emergency_weather_service import EmergencyWeatherService
from app.services.template_service import TemplateService
from tests.fakes import FakeChannelProvider, FakeWeatherProvider, fake_providers


class _TripRepo:
    def __init__(self, trips: list[dict[str, Any]]) -> None:
        self._trips = trips

    def list(self, tenant_id: str | None = None) -> list[dict[str, Any]]:
        if tenant_id is None:
            return list(self._trips)
        return [item for item in self._trips if item.get("tenant_id") == tenant_id]


class _ConfigRepo:
    def get(self, project_id: str, *, tenant_id: str):
        return {"project_id": project_id, "tenant_id": tenant_id, "weather_enabled": True}


def _service(trips, weather, sms, wechat):
    return EmergencyWeatherService(
        trip_repository=_TripRepo(trips),
        project_notification_config_repository=_ConfigRepo(),
        weather_provider=FakeWeatherProvider(weather=weather),
        risk_alert_service=RiskAlertService(),
        template_service=TemplateService(),
        notification_service=NotificationService(providers=fake_providers(sms=sms, wechat=wechat)),
    )


def test_emergency_weather_summary_targets_guests_not_the_operator() -> None:
    sms = FakeChannelProvider(default=(True, "ok"))
    wechat = FakeChannelProvider(default=(True, "ok"))
    trips = [
        {
            "id": "trip-1",
            "tenant_id": "tenant-a",
            "team_id": "TEAM-1",
            "project_id": "proj-1",
            "destination": "阿勒泰",
            "status": "in_progress",
            "start_date": "2026-11-01",
            "end_date": "2026-11-10",
            "participants": 2,
            "guests": [
                {"name": "张三", "phone": "13800138000"},
                {"name": "李四", "phone": "13900139000"},
            ],
        }
    ]
    service = _service(
        trips,
        WeatherInfo(
            destination="阿勒泰",
            condition="暴雪",
            temperature=-20.0,
            warning_level="orange",
            alert_title="暴雪橙色预警",
        ),
        sms,
        wechat,
    )

    result = service.send_summary(
        tenant_id="tenant-a",
        operator_id="admin-1",
        custom_content=None,
        channel="sms",
    )

    assert result["ok"] is True
    assert result["sent_count"] == 2
    assert {call["customer_id"] for call in sms.calls} == {"13800138000", "13900139000"}
    assert all(call["customer_id"] != "admin-1" for call in sms.calls)


def test_emergency_weather_empty_tenant_returns_safe_fallback() -> None:
    sms = FakeChannelProvider(default=(True, "ok"))
    wechat = FakeChannelProvider(default=(True, "ok"))
    service = _service([], WeatherInfo(destination="", condition="晴", temperature=20.0), sms, wechat)

    summary = service.get_summary("tenant-a")
    result = service.send_summary(
        tenant_id="tenant-a",
        operator_id="admin-1",
        custom_content=None,
        channel="sms",
    )

    assert summary["affected_trip_count"] == 0
    assert summary["requires_confirmation"] is True
    assert result["ok"] is False
    assert result["sent_count"] == 0
    assert sms.call_count == 0


def test_emergency_weather_wechat_channel_uses_wechat_provider() -> None:
    sms = FakeChannelProvider(default=(True, "ok"))
    wechat = FakeChannelProvider(default=(True, "ok"))
    trips = [
        {
            "id": "trip-1",
            "tenant_id": "tenant-a",
            "team_id": "TEAM-1",
            "project_id": "proj-1",
            "destination": "阿勒泰",
            "status": "in_progress",
            "start_date": "2026-11-01",
            "end_date": "2026-11-10",
            "participants": 1,
            "guests": [{"name": "张三", "phone": "13800138000"}],
        }
    ]
    service = _service(
        trips,
        WeatherInfo(
            destination="阿勒泰",
            condition="小雨",
            temperature=10.0,
            warning_level="yellow",
            alert_title="道路结冰黄色预警",
            daily_forecast=[
                {
                    "fx_date": "2026-11-05",
                    "text_day": "小雨",
                    "temp_min": 5.0,
                    "temp_max": 12.0,
                    "precip": 3.2,
                }
            ],
        ),
        sms,
        wechat,
    )

    result = service.send_summary(
        tenant_id="tenant-a",
        operator_id="admin-1",
        custom_content="custom",
        channel="wechat_work_group",
    )

    assert result["ok"] is True
    assert result["sent_count"] == 1
    assert sms.call_count == 0
    assert wechat.call_count == 1
    assert wechat.calls[0]["content"] == "custom"
