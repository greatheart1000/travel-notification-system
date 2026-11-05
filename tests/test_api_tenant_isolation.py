from __future__ import annotations

from fastapi.testclient import TestClient


def _login(client: TestClient, username: str, password: str = "123456") -> str:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_tenant_boundary_rejects_cross_tenant_trip_and_history(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TRAVEL_NOTIFICATION_DB_DIR", str(tmp_path))
    monkeypatch.setenv("NOTIFICATION_QUEUE_INTERVAL_SECONDS", "3600")
    from app.api.http import create_app

    app = create_app()
    with TestClient(app) as client:
        admin_token = _login(client, "admin")
        partner_token = _login(client, "partner")

        created = client.post(
            "/api/trips",
            headers=_auth(admin_token),
            json={
                "destination": "租户A专属团",
                "team": "TEAM-TENANT-A",
                "start_date": "2026-12-01",
                "end_date": "2026-12-03",
                "participants": 1,
            },
        )
        assert created.status_code == 201
        trip_id = created.json()["data"]["trip"]["id"]

        cross_read = client.get(f"/api/trips/{trip_id}", headers=_auth(partner_token))
        assert cross_read.status_code == 403

        partner_trips = client.get("/api/trips", headers=_auth(partner_token))
        assert partner_trips.status_code == 200
        assert all(item["id"] != trip_id for item in partner_trips.json()["data"]["items"])

        sent = client.post(
            "/api/notifications/send",
            headers=_auth(admin_token),
            json={
                "customer_name": "张三",
                "customer_phone": "13800138000",
                "custom_content": "tenant-a only",
                "channel": "sms",
                "trip_id": trip_id,
            },
        )
        assert sent.status_code == 200

        partner_history = client.get(
            "/api/notifications/recent",
            headers=_auth(partner_token),
        )
        assert partner_history.status_code == 200
        assert partner_history.json()["data"]["total"] == 0

        partner_rules = client.get(
            "/api/notifications/rules",
            headers=_auth(partner_token),
        )
        assert partner_rules.status_code == 200
        assert partner_rules.json()["data"]["items"] == []


def test_admin_can_manage_tenant_notification_config(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TRAVEL_NOTIFICATION_DB_DIR", str(tmp_path))
    monkeypatch.setenv("NOTIFICATION_QUEUE_INTERVAL_SECONDS", "3600")
    from app.api.http import create_app

    app = create_app()
    with TestClient(app) as client:
        admin_token = _login(client, "admin")
        partner_token = _login(client, "partner")

        forbidden = client.get(
            "/api/admin/tenant-notification-config",
            headers=_auth(partner_token),
        )
        assert forbidden.status_code == 403

        updated = client.put(
            "/api/admin/tenant-notification-config",
            headers=_auth(admin_token),
            json={
                "wechat_webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=tenant-a",
                "sms_provider": "mock",
                "sms_sign_name": "TravelHub",
                "sms_template_code": "SMS_001",
            },
        )
        assert updated.status_code == 200

        fetched = client.get(
            "/api/admin/tenant-notification-config",
            headers=_auth(admin_token),
        )
        assert fetched.status_code == 200
        config = fetched.json()["data"]["config"]
        assert config["tenant_id"] == "tenant-a"
        assert config["sms_provider"] == "mock"
        assert config["wechat_webhook_url"].endswith("key=tenant-a")
