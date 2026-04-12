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
