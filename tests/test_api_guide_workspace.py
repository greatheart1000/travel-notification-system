from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient


def _login(client: TestClient, username: str, password: str = "123456") -> str:
    response = client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_guide_workspace_shows_assigned_trip_and_latest_content(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TRAVEL_NOTIFICATION_DB_DIR", str(tmp_path))
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("NOTIFICATION_QUEUE_INTERVAL_SECONDS", "3600")
    monkeypatch.setenv("WECHAT_WEBHOOK_URL", "")
    from app.api.http import create_app

    app = create_app()
    from types import SimpleNamespace
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
    with TestClient(app) as client:
        admin_token = _login(client, "admin")
        created_guide = client.post(
            "/api/admin/users",
            headers=_auth(admin_token),
            json={
                "username": "guide-workspace",
                "password": "Guide123456",
                "role": "guide",
            },
        )
        assert created_guide.status_code == 201, created_guide.text
        guide_id = created_guide.json()["data"]["id"]
        other_guide = client.post(
            "/api/admin/users",
            headers=_auth(admin_token),
            json={
                "username": "guide-other",
                "password": "Guide123456",
                "role": "guide",
            },
        )
        assert other_guide.status_code == 201, other_guide.text

        start = date.today() + timedelta(days=2)
        created_trip = client.post(
            "/api/trips",
            headers=_auth(admin_token),
            json={
                "destination": "吐鲁番火焰山",
                "team": "TEAM-GUIDE-WORKSPACE",
                "start_date": start.isoformat(),
                "end_date": (start + timedelta(days=2)).isoformat(),
                "participants": 2,
            },
        )
        assert created_trip.status_code == 201, created_trip.text
        trip_id = created_trip.json()["data"]["trip"]["id"]
        client.put(
            f"/api/trips/{trip_id}",
            headers=_auth(admin_token),
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
        client.put(
            f"/api/trips/{trip_id}/assignments",
            headers=_auth(admin_token),
            json={"user_ids": [guide_id]},
        )

        guide_token = _login(client, "guide-workspace", "Guide123456")
        executed = client.post(
            f"/api/trips/{trip_id}/workflow/execute?step=pre_flight_notice",
            headers=_auth(guide_token),
            json={},
        )
        assert executed.status_code == 502

        workspace = client.get("/api/guide/workspace", headers=_auth(guide_token))
        assert workspace.status_code == 200, workspace.text
        data = workspace.json()["data"]
        assert data["stats"]["assigned_trips"] == 1
        assert data["stats"]["due_today"] == 1
        assert data["stats"]["group_missing"] == 1
        assert data["stats"]["weather_alerts"] == 1
        trip = data["trips"][0]
        assert trip["id"] == trip_id
        assert trip["stage"] == "pre_trip"
        assert trip["action_label"] == "发送行前提醒"
        assert trip["group_configured"] is False
        assert "暴雪蓝色预警" in trip["weather_warning"]
        assert trip["latest_notification"]["status"] == "failed"
        assert trip["latest_notification"]["content"]
        assert "各位团友" in trip["latest_notification"]["content"]
        assert data["recent_notifications"][0]["trip_id"] == trip_id

        plan_response = client.get(
            f"/api/trips/{trip_id}/message-plan", headers=_auth(guide_token)
        )
        assert plan_response.status_code == 200, plan_response.text
        plan = plan_response.json()["data"]
        assert plan["group_configured"] is False
        assert len(plan["items"]) == 12
        day_one_morning = next(
            item
            for item in plan["items"]
            if item["date"] == start.isoformat() and item["slot"] == "morning"
        )
        assert "火焰山" in day_one_morning["content"]
        assert {item["slot"] for item in plan["items"]} >= {
            "morning",
            "afternoon",
            "evening",
        }

        other_token = _login(client, "guide-other", "Guide123456")
        other_workspace = client.get("/api/guide/workspace", headers=_auth(other_token))
        assert other_workspace.status_code == 200
        assert other_workspace.json()["data"]["trips"] == []
