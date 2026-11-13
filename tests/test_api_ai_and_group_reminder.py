from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.models import Channel
from tests.fakes import FakeChannelProvider


def _login(client: TestClient, username: str, password: str = "123456") -> str:
    response = client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_app(monkeypatch, tmp_path):
    monkeypatch.setenv("TRAVEL_NOTIFICATION_DB_DIR", str(tmp_path))
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("NOTIFICATION_QUEUE_INTERVAL_SECONDS", "3600")
    monkeypatch.delenv("GLM_API_KEY", raising=False)
    monkeypatch.setenv("WECHAT_WEBHOOK_URL", "")
    from app.api.http import create_app

    return create_app()


def test_ai_polish_uses_local_fallback_without_key(monkeypatch, tmp_path) -> None:
    app = _create_app(monkeypatch, tmp_path)
    with TestClient(app) as client:
        token = _login(client, "admin")
        response = client.post(
            "/api/notifications/ai-polish",
            headers=_auth(token),
            json={
                "content": "请知悉，明天7点集合!! 请带好身份证。",
                "destination": "喀纳斯",
                "scene": "每日行程提醒",
            },
        )
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert data["provider"] == "local"
        assert data["content"].startswith("请留意")
        assert "请留意" in data["content"]
        assert "!!" not in data["content"]
        assert "！" not in data["content"]
        assert "祝大家旅途愉快" not in data["content"]


def test_group_reminder_requires_wecom_webhook(monkeypatch, tmp_path) -> None:
    app = _create_app(monkeypatch, tmp_path)
    with TestClient(app) as client:
        token = _login(client, "admin")
        created = client.post(
            "/api/trips",
            headers=_auth(token),
            json={
                "destination": "未配置群提醒测试团",
                "team": "TEAM-GROUP-NO-WEBHOOK",
                "start_date": "2026-12-01",
                "end_date": "2026-12-02",
                "participants": 1,
            },
        )
        trip_id = created.json()["data"]["trip"]["id"]
        preview = client.post(
            f"/api/trips/{trip_id}/group-reminder",
            headers=_auth(token),
            json={"message": "明天7点集合，请带好身份证。", "use_ai": True, "dry_run": True},
        )
        assert preview.status_code == 200, preview.text
        preview_data = preview.json()["data"]
        assert preview_data["dry_run"] is True
        assert "明天7点集合" in preview_data["message"]
        assert preview_data["sent_at"] is None

        generated = client.post(
            f"/api/trips/{trip_id}/group-reminder",
            headers=_auth(token),
            json={"use_ai": True, "dry_run": True},
        )
        assert generated.status_code == 200, generated.text
        generated_message = generated.json()["data"]["message"]
        assert "行前提醒" in generated_message
        assert "2026-12-01" in generated_message

        response = client.post(
            f"/api/trips/{trip_id}/group-reminder",
            headers=_auth(token),
            json={"message": "明天7点集合", "use_ai": False},
        )
        assert response.status_code == 400
        assert "企业微信群 Webhook" in response.json()["error"]

        overview = client.get("/api/admin/team-overview", headers=_auth(token))
        assert overview.status_code == 200, overview.text
        missing_group = overview.json()["data"]["trips_without_group"]
        assert any(item["id"] == trip_id for item in missing_group)


def test_group_reminder_content_is_visible_to_admin_by_guide_trip(
    monkeypatch, tmp_path
) -> None:
    app = _create_app(monkeypatch, tmp_path)
    with TestClient(app) as client:
        admin_token = _login(client, "admin")
        guide = client.post(
            "/api/admin/users",
            headers=_auth(admin_token),
            json={
                "username": "guide-visibility",
                "password": "Guide123456",
                "role": "guide",
            },
        )
        assert guide.status_code == 201, guide.text
        guide_id = guide.json()["data"]["id"]

        created = client.post(
            "/api/trips",
            headers=_auth(admin_token),
            json={
                "destination": "群提醒可见性测试团",
                "team": "TEAM-GROUP-VISIBLE",
                "start_date": "2026-12-05",
                "end_date": "2026-12-07",
                "participants": 2,
            },
        )
        trip_id = created.json()["data"]["trip"]["id"]
        updated = client.put(
            f"/api/trips/{trip_id}",
            headers=_auth(admin_token),
            json={
                "itinerary": [
                    {
                        "date": "2026-12-05",
                        "type": "商务车",
                        "activity": "喀纳斯景区游览",
                        "hotel": "湖区酒店",
                    }
                ],
            },
        )
        assert updated.status_code == 200, updated.text
        webhook = client.put(
            f"/api/trips/{trip_id}/webhook",
            headers=_auth(admin_token),
            json={
                "webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test"
            },
        )
        assert webhook.status_code == 200, webhook.text
        assigned = client.put(
            f"/api/trips/{trip_id}/assignments",
            headers=_auth(admin_token),
            json={"user_ids": [guide_id]},
        )
        assert assigned.status_code == 200, assigned.text

        fake = FakeChannelProvider(default=(True, "ok"))
        app.state.ctx.notification_service.providers = {
            Channel.WECHAT_WORK_GROUP: fake
        }
        sent = client.post(
            f"/api/trips/{trip_id}/group-reminder",
            headers=_auth(admin_token),
            json={
                "message": "各位团友，明天7点大堂集合，请带好身份证和保暖外套。",
                "use_ai": True,
                "scene": "每日行程提醒",
            },
        )
        assert sent.status_code == 200, sent.text
        sent_data = sent.json()["data"]
        assert sent_data["provider"] == "local"
        assert fake.call_count == 1
        assert "明天7点大堂集合" in fake.calls[0]["content"]

        overview = client.get(
            "/api/admin/team-overview", headers=_auth(admin_token)
        )
        assert overview.status_code == 200, overview.text
        data = overview.json()["data"]
        member = next(item for item in data["members"] if item["id"] == guide_id)
        assert [trip["id"] for trip in member["assigned_trips"]] == [trip_id]
        assert member["notification_count"] >= 1
        latest = member["recent_notifications"][0]
        assert latest["content"]
        assert "明天7点大堂集合" in latest["content"]
        assert latest["operator_name"] == "陈静"
        assert latest["channel"] == "wechat_work_group"
        assert any(item["trip_id"] == trip_id for item in data["recent_notifications"])
        assert data["stats"]["assigned_trips"] >= 1


def test_booking_confirmation_sends_sms_once(monkeypatch, tmp_path) -> None:
    app = _create_app(monkeypatch, tmp_path)
    with TestClient(app) as client:
        token = _login(client, "admin")
        created = client.post(
            "/api/trips",
            headers=_auth(token),
            json={
                "destination": "参团短信测试团",
                "team": "TEAM-BOOKING",
                "start_date": "2026-12-10",
                "end_date": "2026-12-12",
                "participants": 2,
            },
        )
        trip_id = created.json()["data"]["trip"]["id"]
        updated = client.put(
            f"/api/trips/{trip_id}",
            headers=_auth(token),
            json={
                "guests": [
                    {"name": "张三", "phone": "13800000001"},
                    {"name": "李四", "phone": "13800000002"},
                    {"name": "无手机号"},
                ]
            },
        )
        assert updated.status_code == 200, updated.text

        fake = FakeChannelProvider(default=(True, "ok"))
        app.state.ctx.notification_service.providers = {Channel.SMS: fake}
        sent = client.post(
            f"/api/trips/{trip_id}/booking-confirmation",
            headers=_auth(token),
        )
        assert sent.status_code == 200, sent.text
        data = sent.json()["data"]
        assert data["sent"] == 2
        assert data["failed"] == 0
        assert fake.call_count == 2
        assert all("参团成功" in call["content"] for call in fake.calls)
        assert "张三" in fake.calls[0]["content"]

        repeated = client.post(
            f"/api/trips/{trip_id}/booking-confirmation",
            headers=_auth(token),
        )
        assert repeated.status_code == 200
        assert repeated.json()["data"]["sent"] == 0
        assert repeated.json()["data"]["skipped"] == 2
        assert fake.call_count == 2


def test_reminder_suggestion_is_region_aware(monkeypatch, tmp_path) -> None:
    from datetime import date, timedelta

    app = _create_app(monkeypatch, tmp_path)
    start = date.today() + timedelta(days=2)
    with TestClient(app) as client:
        token = _login(client, "admin")
        created = client.post(
            "/api/trips",
            headers=_auth(token),
            json={
                "destination": "吐鲁番火焰山",
                "team": "TEAM-SUGGESTION",
                "start_date": start.isoformat(),
                "end_date": (start + timedelta(days=2)).isoformat(),
                "participants": 2,
            },
        )
        trip_id = created.json()["data"]["trip"]["id"]
        client.put(
            f"/api/trips/{trip_id}",
            headers=_auth(token),
            json={
                "itinerary": [
                    {
                        "date": start.isoformat(),
                        "type": "商务车",
                        "activity": "火焰山与葡萄沟游览",
                        "hotel": "吐鲁番酒店",
                    }
                ]
            },
        )

        def no_weather(*_args, **_kwargs):
            raise RuntimeError("weather unavailable")

        monkeypatch.setattr(app.state.ctx.weather_provider, "get_weather", no_weather)
        from types import SimpleNamespace

        app.state.ctx.weather_query_service = SimpleNamespace(
            list_region=lambda _region: {"cities": []}
        )
        response = client.get(
            f"/api/trips/{trip_id}/reminder-suggestion",
            headers=_auth(token),
        )
        assert response.status_code == 200, response.text
        suggestion = response.json()["data"]["suggestion"]
        assert suggestion is not None
        assert suggestion["situation"] == "pre_trip"
        assert "吐鲁番" in suggestion["content"]
        assert "防晒" in suggestion["content"]
        assert suggestion["provider"] == "local"

        app.state.ctx.weather_query_service = SimpleNamespace(
            list_region=lambda _region: {
                "cities": [
                    {
                        "city": "吐鲁番",
                        "weather": "暴雪",
                        "temp": -5,
                        "warning": "暴雪蓝色预警",
                        "warning_title": "吐鲁番市气象台发布暴雪蓝色预警",
                        "source": "qweather",
                    }
                ]
            }
        )
        weather_response = client.get(
            f"/api/trips/{trip_id}/reminder-suggestion",
            headers=_auth(token),
        )
        weather_suggestion = weather_response.json()["data"]["suggestion"]
        assert weather_suggestion["situation"] == "weather_alert"
        assert len(weather_suggestion["variants"]) == 2
        assert "防滑" in weather_suggestion["content"]
