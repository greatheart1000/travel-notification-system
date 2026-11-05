from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.models import Channel
from app.modules.integration.weather_provider import WeatherInfo
from tests.fakes import FakeChannelProvider, FakeWeatherProvider


def _admin_token(client: TestClient) -> str:
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "123456"},
    )
    assert response.status_code == 200
    body = response.json()
    return body["data"]["access_token"]


def test_trigger_weather_check_sends_to_guests_of_the_current_tenant(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TRAVEL_NOTIFICATION_DB_DIR", str(tmp_path))
    monkeypatch.setenv("NOTIFICATION_QUEUE_INTERVAL_SECONDS", "3600")
    from app.api.http import create_app

    app = create_app()
    ctx = app.state.ctx
    sms = FakeChannelProvider(default=(True, "ok"))
    wechat = FakeChannelProvider(default=(True, "ok"))
    ctx.notification_service.providers = {
        Channel.SMS: sms,
        Channel.WECHAT_WORK_GROUP: wechat,
    }
    ctx.weather_provider = FakeWeatherProvider(
        weather=WeatherInfo(
            destination="阿勒泰",
            condition="暴雪",
            temperature=-20.0,
            warning_level="orange",
            alert_title="暴雪橙色预警",
        )
    )
    ctx.trip_repository.create(
        {
            "id": "trip-weather-1",
            "tenant_id": "tenant-a",
            "team_id": "TEAM-1",
            "project_id": "proj-1",
            "destination": "阿勒泰",
            "status": "in_progress",
            "start_date": "2026-11-01",
            "end_date": "2026-11-10",
            "guests": [{"name": "张三", "phone": "13800138000"}],
        }
    )

    with TestClient(app) as client:
        token = _admin_token(client)
        response = client.post(
            "/api/admin/trigger-weather-check",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json()["data"]["triggered_notifications"] >= 1
    assert any(call["customer_id"] == "13800138000" for call in sms.calls)


def test_create_trip_does_not_send_sms_to_the_operator_id(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TRAVEL_NOTIFICATION_DB_DIR", str(tmp_path))
    monkeypatch.setenv("NOTIFICATION_QUEUE_INTERVAL_SECONDS", "3600")
    from app.api.http import create_app

    app = create_app()
    sms = FakeChannelProvider(default=(True, "ok"))
    wechat = FakeChannelProvider(default=(True, "ok"))
    app.state.ctx.notification_service.providers = {
        Channel.SMS: sms,
        Channel.WECHAT_WORK_GROUP: wechat,
    }

    with TestClient(app) as client:
        token = _admin_token(client)
        response = client.post(
            "/api/trips",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "destination": "测试团",
                "team": "TEAM-NEW",
                "start_date": "2026-12-01",
                "end_date": "2026-12-03",
                "participants": 2,
            },
        )

    assert response.status_code == 201
    assert sms.call_count == 0
    assert response.json()["data"]["notification"]["status"] == "skipped"
