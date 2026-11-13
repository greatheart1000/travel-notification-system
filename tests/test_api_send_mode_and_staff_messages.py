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


def _build_app(monkeypatch, tmp_path):
    monkeypatch.setenv("TRAVEL_NOTIFICATION_DB_DIR", str(tmp_path))
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("NOTIFICATION_QUEUE_INTERVAL_SECONDS", "3600")
    monkeypatch.setenv("WECHAT_WEBHOOK_URL", "")
    from app.api.http import create_app

    return create_app()


def test_send_mode_can_be_switched_per_trip_and_requires_access(monkeypatch, tmp_path) -> None:
    app = _build_app(monkeypatch, tmp_path)
    with TestClient(app) as client:
        admin_token = _login(client, "admin")
        guide = client.post(
            "/api/admin/users",
            headers=_auth(admin_token),
            json={
                "username": "guide-send-mode",
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
                "destination": "喀纳斯",
                "team": "TEAM-SEND-MODE",
                "start_date": date.today().isoformat(),
                "end_date": (date.today() + timedelta(days=2)).isoformat(),
                "participants": 2,
            },
        )
        assert created.status_code == 201, created.text
        trip_id = created.json()["data"]["trip"]["id"]
        assert created.json()["data"]["trip"]["send_mode"] == "auto"

        invalid = client.put(
            f"/api/trips/{trip_id}/send-mode",
            headers=_auth(admin_token),
            json={"mode": "sometimes"},
        )
        assert invalid.status_code == 400

        switched = client.put(
            f"/api/trips/{trip_id}/send-mode",
            headers=_auth(admin_token),
            json={"mode": "approval"},
        )
        assert switched.status_code == 200, switched.text
        assert switched.json()["data"]["send_mode"] == "approval"
        detail = client.get(f"/api/trips/{trip_id}", headers=_auth(admin_token))
        assert detail.status_code == 200, detail.text
        assert detail.json()["data"]["send_mode"] == "approval"

        # An unassigned guide cannot change another guide's trip.
        guide_token = _login(client, "guide-send-mode", "Guide123456")
        denied = client.put(
            f"/api/trips/{trip_id}/send-mode",
            headers=_auth(guide_token),
            json={"mode": "auto"},
        )
        assert denied.status_code == 403

        client.put(
            f"/api/trips/{trip_id}/assignments",
            headers=_auth(admin_token),
            json={"user_ids": [guide_id]},
        )
        guide_switch = client.put(
            f"/api/trips/{trip_id}/send-mode",
            headers=_auth(guide_token),
            json={"mode": "auto"},
        )
        assert guide_switch.status_code == 200, guide_switch.text
        assert guide_switch.json()["data"]["send_mode"] == "auto"

        client.put(
            f"/api/trips/{trip_id}/send-mode",
            headers=_auth(guide_token),
            json={"mode": "approval"},
        )
        workspace = client.get("/api/guide/workspace", headers=_auth(guide_token))
        assert workspace.status_code == 200, workspace.text
        workspace_trip = next(
            item for item in workspace.json()["data"]["trips"] if item["id"] == trip_id
        )
        assert workspace_trip["send_mode"] == "approval"

        team = client.get("/api/admin/team-overview", headers=_auth(admin_token))
        assert team.status_code == 200, team.text
        team_trip = next(
            item
            for member in team.json()["data"]["members"]
            for item in member["assigned_trips"]
            if item["id"] == trip_id
        )
        assert team_trip["send_mode"] == "approval"


def test_staff_messages_are_role_specific_and_can_be_sent_independently(
    monkeypatch, tmp_path
) -> None:
    app = _build_app(monkeypatch, tmp_path)
    with TestClient(app) as client:
        admin_token = _login(client, "admin")
        guide = client.post(
            "/api/admin/users",
            headers=_auth(admin_token),
            json={
                "username": "guide-staff-messages",
                "password": "Guide123456",
                "role": "guide",
            },
        )
        assert guide.status_code == 201, guide.text
        guide_id = guide.json()["data"]["id"]
        start = date.today()
        created = client.post(
            "/api/trips",
            headers=_auth(admin_token),
            json={
                "destination": "伊犁",
                "team": "TEAM-STAFF-MESSAGES",
                "start_date": start.isoformat(),
                "end_date": (start + timedelta(days=1)).isoformat(),
                "participants": 2,
            },
        )
        assert created.status_code == 201, created.text
        trip_id = created.json()["data"]["trip"]["id"]
        client.put(
            f"/api/trips/{trip_id}/assignments",
            headers=_auth(admin_token),
            json={"user_ids": [guide_id]},
        )
        staff = client.put(
            f"/api/trips/{trip_id}/staff",
            headers=_auth(admin_token),
            json={
                "staff": [
                    {"role": "manager", "name": "马负责人", "phone": "13900000001"},
                    {"role": "concierge", "name": "古丽管家", "phone": "13900000002"},
                    {
                        "role": "driver",
                        "name": "张师傅",
                        "phone": "13900000003",
                        "recipient_channel": "sms",
                        "recipient_address": "13900000003",
                    },
                ]
            },
        )
        assert staff.status_code == 200, staff.text
        staff_config = client.get(
            f"/api/trips/{trip_id}/staff", headers=_auth(admin_token)
        )
        assert staff_config.status_code == 200, staff_config.text
        driver_config = next(
            item for item in staff_config.json()["data"]["staff"] if item["role"] == "driver"
        )
        assert driver_config["recipient_channel"] == "sms"
        assert driver_config["recipient_address"] == "13900000003"

        guide_token = _login(client, "guide-staff-messages", "Guide123456")
        response = client.get(
            f"/api/trips/{trip_id}/staff-messages", headers=_auth(guide_token)
        )
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert len(data["items"]) == 6
        assert {item["role"] for item in data["items"]} == {
            "manager",
            "concierge",
            "driver",
        }
        assert all(item["content"] for item in data["items"])
        assert all("{{" not in item["content"] for item in data["items"])
        morning_manager = next(
            item
            for item in data["items"]
            if item["role"] == "manager" and item["slot"] == "morning"
        )
        assert "马负责人" in morning_manager["content"]
        afternoon_driver = next(
            item
            for item in data["items"]
            if item["role"] == "driver" and item["slot"] == "afternoon"
        )
        # "afternoon" maps to the noon_* playbook template, not a missing key.
        assert afternoon_driver["content"]
        assert "张师傅" in afternoon_driver["content"]
        assert afternoon_driver["channel"] == "sms"
        assert afternoon_driver["recipient_label"] == "短信 13900000003"

        sent = client.post(
            f"/api/trips/{trip_id}/staff-messages/driver/send",
            headers=_auth(guide_token),
            json={
                "slot": "morning",
                "content": "张师傅早上好，今天伊犁有小雨，请减速慢行。",
            },
        )
        assert sent.status_code == 200, sent.text
        assert sent.json()["data"]["role"] == "driver"
        assert sent.json()["data"]["channel"] == "sms"

        refreshed = client.get(
            f"/api/trips/{trip_id}/staff-messages", headers=_auth(guide_token)
        )
        refreshed_items = refreshed.json()["data"]["items"]
        driver_morning = next(
            item
            for item in refreshed_items
            if item["role"] == "driver" and item["slot"] == "morning"
        )
        assert driver_morning["status"] == "sent"
        assert driver_morning["content"] == "张师傅早上好，今天伊犁有小雨，请减速慢行。"
        attempts = app.state.ctx.notification_attempt_repository.list_history(
            limit=None, trip_id=trip_id
        )
        staff_attempt = next(
            item
            for item in attempts
            if item.get("schedule_key")
            == f"{trip_id}:{date.today().isoformat()}:staff:driver:morning"
        )
        assert staff_attempt["ok"] is True
        assert staff_attempt["operator_id"] == guide_id


def test_staff_message_send_validates_role_and_recipient(monkeypatch, tmp_path) -> None:
    app = _build_app(monkeypatch, tmp_path)
    with TestClient(app) as client:
        admin_token = _login(client, "admin")
        created = client.post(
            "/api/trips",
            headers=_auth(admin_token),
            json={
                "destination": "吐鲁番",
                "team": "TEAM-STAFF-VALIDATION",
                "start_date": date.today().isoformat(),
                "end_date": (date.today() + timedelta(days=1)).isoformat(),
                "participants": 1,
            },
        )
        assert created.status_code == 201, created.text
        trip_id = created.json()["data"]["trip"]["id"]

        messages = client.get(
            f"/api/trips/{trip_id}/staff-messages", headers=_auth(admin_token)
        )
        assert messages.status_code == 200, messages.text
        contents = [item["content"] for item in messages.json()["data"]["items"]]
        assert all(content for content in contents)
        assert all("管家管家" not in content for content in contents)
        assert all("司机司机" not in content for content in contents)
        assert all("（电话：）" not in content for content in contents)

        bad_role = client.post(
            f"/api/trips/{trip_id}/staff-messages/nobody/send",
            headers=_auth(admin_token),
            json={"slot": "morning"},
        )
        assert bad_role.status_code == 400

        no_group = client.post(
            f"/api/trips/{trip_id}/staff-messages/manager/send",
            headers=_auth(admin_token),
            json={"slot": "morning"},
        )
        assert no_group.status_code == 400
        assert "企业微信群" in no_group.json()["detail"]
