from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.http import app, reset_state


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def test_auth_login_and_role_resolution() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)

    admin_token = _login(client, "admin", "123456")
    user_token = _login(client, "user", "123456")

    admin_me = client.get("/api/users/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert admin_me.status_code == 200
    assert admin_me.json()["data"]["role"] == "admin"

    user_me = client.get("/api/users/me", headers={"Authorization": f"Bearer {user_token}"})
    assert user_me.status_code == 200
    assert user_me.json()["data"]["role"] == "user"


def test_preferences_read_write() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)
    user_token = _login(client, "user", "123456")
    headers = {"Authorization": f"Bearer {user_token}"}

    initial = client.get("/api/preferences/me", headers=headers)
    assert initial.status_code == 200
    assert "channels" in initial.json()["data"]

    updated = client.put(
        "/api/preferences/me",
        headers=headers,
        json={"channels": ["email", "sms"], "quiet_hours": [22, 6], "allow_marketing": False},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["channels"] == ["email", "sms"]
    assert updated.json()["data"]["quiet_hours"] == [22, 6]
    assert updated.json()["data"]["allow_marketing"] is False


def test_template_crud_and_admin_guard() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)

    admin_token = _login(client, "admin", "123456")
    user_token = _login(client, "user", "123456")

    forbidden = client.post(
        "/api/templates",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "name": "普通用户创建",
            "content": "{{customer_name}}，你好",
            "channel": "sms",
            "notification_type": "daily_reminder",
            "is_active": True,
        },
    )
    assert forbidden.status_code == 403

    create = client.post(
        "/api/templates",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "出发前提醒",
            "content": "{{customer_name}}，您的{{destination}}行程即将开始。",
            "channel": "sms",
            "notification_type": "daily_reminder",
            "is_active": True,
        },
    )
    assert create.status_code == 201
    template_id = create.json()["data"]["id"]

    listed = client.get("/api/templates", headers={"Authorization": f"Bearer {admin_token}"})
    assert listed.status_code == 200
    assert any(item["id"] == template_id for item in listed.json()["data"]["items"])

    detail = client.get(
        f"/api/templates/{template_id}", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert detail.status_code == 200

    updated = client.put(
        f"/api/templates/{template_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_active": False, "content": "变更后的模板内容"},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["is_active"] is False

    deleted = client.delete(
        f"/api/templates/{template_id}", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert deleted.status_code == 200

    missing = client.get(
        f"/api/templates/{template_id}", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert missing.status_code == 404


def test_trip_creation_triggers_notification_history_and_audit() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)
    user_token = _login(client, "user", "123456")
    headers = {"Authorization": f"Bearer {user_token}"}

    created = client.post(
        "/api/trips",
        headers=headers,
        json={
            "destination": "阿勒泰 - 禾木",
            "team": "TEAM-009",
            "start_date": "2026-05-01",
            "end_date": "2026-05-03",
            "participants": 20,
        },
    )
    assert created.status_code == 201
    trip_id = created.json()["data"]["trip"]["id"]
    assert created.json()["data"]["notification"]["ok"] is True

    history = client.get(f"/api/notifications/history?trip_id={trip_id}&limit=10", headers=headers)
    assert history.status_code == 200
    assert history.json()["data"]["total"] >= 1

    timeline = client.get(f"/api/trips/{trip_id}/timeline", headers=headers)
    assert timeline.status_code == 200
    actions = {item["action"] for item in timeline.json()["data"]["audit_logs"]}
    assert "trip_created" in actions
    assert "notification_dispatched" in actions


def test_health_check_detail() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["data"]["status"] == "ok"

    detail = client.get("/api/health/detail")
    assert detail.status_code == 200
    assert detail.json()["data"]["status"] == "ok"
    assert "components" in detail.json()["data"]


def test_dashboard_and_analytics_return_aggregated_data() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)
    user_token = _login(client, "user", "123456")
    headers = {"Authorization": f"Bearer {user_token}"}

    for destination in ("阿勒泰", "喀纳斯"):
        created = client.post(
            "/api/trips",
            headers=headers,
            json={
                "destination": destination,
                "team": "TEAM-ANALYTICS",
                "start_date": "2026-06-01",
                "end_date": "2026-06-05",
                "participants": 8,
            },
        )
        assert created.status_code == 201

    dashboard = client.get("/api/dashboard/stats", headers=headers)
    assert dashboard.status_code == 200
    dashboard_data = dashboard.json()["data"]
    assert dashboard_data["today_notifications"] >= 2
    assert dashboard_data["active_trips"] >= 2

    analytics = client.get("/api/analytics/metrics", headers=headers)
    assert analytics.status_code == 200
    analytics_data = analytics.json()["data"]
    assert analytics_data["metrics"]["notification_success_rate"] != "0.0%"
    assert len(analytics_data["channel_performance"]) >= 1
    assert len(analytics_data["top_trips"]) >= 1


def test_update_trip_rejects_blank_team_fields_and_keeps_original_value() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)
    user_token = _login(client, "user", "123456")
    headers = {"Authorization": f"Bearer {user_token}"}

    created = client.post(
        "/api/trips",
        headers=headers,
        json={
            "destination": "喀纳斯",
            "team": "TEAM-ORIGINAL",
            "start_date": "2026-06-01",
            "end_date": "2026-06-05",
            "participants": 12,
        },
    )
    assert created.status_code == 201
    trip_id = created.json()["data"]["trip"]["id"]

    blank_team = client.put(
        f"/api/trips/{trip_id}",
        headers=headers,
        json={"team": "   "},
    )
    assert blank_team.status_code == 400

    blank_team_id = client.put(
        f"/api/trips/{trip_id}",
        headers=headers,
        json={"team_id": "   "},
    )
    assert blank_team_id.status_code == 400

    detail = client.get(f"/api/trips/{trip_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["data"]["team_id"] == "TEAM-ORIGINAL"
    assert detail.json()["data"]["team"] == "TEAM-ORIGINAL"


def test_notification_rules_contract_smoke() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)
    admin_token = _login(client, "admin", "123456")
    headers = {"Authorization": f"Bearer {admin_token}"}

    listed_before = client.get("/api/notifications/rules", headers=headers)
    assert listed_before.status_code == 200
    assert listed_before.json()["code"] == 200
    assert "message" in listed_before.json()

    created = client.post(
        "/api/notifications/rules",
        headers=headers,
        json={
            "name": "规则契约冒烟",
            "stage": "before_departure",
            "time_slot": "AM",
            "scene": "天气",
            "channels": ["短信", "企业微信"],
            "priority": 10,
            "enabled": True,
            "conditions": {"rain": True},
        },
    )
    assert created.status_code == 201
    created_data = created.json()["data"]
    rule_id = created_data["id"]
    assert created_data["stage"] == "pre_trip"
    assert created_data["time_slot"] == "morning"
    assert created_data["scene"] == "weather_alert"
    assert created_data["channels"] == ["sms", "wechat_work_group"]

    fetched = client.get(f"/api/notifications/rules/{rule_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["data"]["id"] == rule_id

    updated = client.put(
        f"/api/notifications/rules/{rule_id}",
        headers=headers,
        json={"enabled": False, "time_slot": "night", "priority": 5},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["enabled"] is False
    assert updated.json()["data"]["time_slot"] == "night"
    assert updated.json()["data"]["priority"] == 5

    invalid = client.post(
        "/api/notifications/rules",
        headers=headers,
        json={"name": "非法规则", "stage": "bad-stage", "time_slot": "morning", "scene": "normal"},
    )
    assert invalid.status_code == 400
    assert invalid.json()["code"] == 400

    deleted = client.delete(f"/api/notifications/rules/{rule_id}", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["data"]["deleted"] is True

    listed_after = client.get("/api/notifications/rules", headers=headers)
    assert listed_after.status_code == 200
    assert all(item["id"] != rule_id for item in listed_after.json()["data"]["items"])
