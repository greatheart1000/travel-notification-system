from __future__ import annotations

from fastapi.testclient import TestClient


def _login(client: TestClient, username: str, password: str = "123456") -> str:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_guide_cannot_access_tenant_billing_or_analytics(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TRAVEL_NOTIFICATION_DB_DIR", str(tmp_path))
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("NOTIFICATION_QUEUE_INTERVAL_SECONDS", "3600")
    from app.api.http import create_app

    app = create_app()
    with TestClient(app) as client:
        admin_token = _login(client, "admin")
        created = client.post(
            "/api/admin/users",
            headers=_auth(admin_token),
            json={"username": "guide-role", "password": "Guide123456", "role": "guide"},
        )
        assert created.status_code == 201, created.text
        guide_token = _login(client, "guide-role", "Guide123456")

        assert client.get("/api/billing/subscription", headers=_auth(guide_token)).status_code == 403
        assert client.get("/api/billing/orders", headers=_auth(guide_token)).status_code == 403
        assert client.get("/api/analytics/metrics", headers=_auth(guide_token)).status_code == 403
        assert (
            client.post(
                "/api/trips",
                headers=_auth(guide_token),
                json={
                    "destination": "导游不应创建",
                    "team": "TEAM-GUIDE-CREATE",
                    "start_date": "2026-12-20",
                    "end_date": "2026-12-21",
                    "participants": 1,
                },
            ).status_code
            == 403
        )
        assert client.get("/api/trips", headers=_auth(guide_token)).status_code == 200
        assert (
            client.get("/api/notifications/rules", headers=_auth(guide_token)).status_code
            == 200
        )


def test_production_skips_demo_seed_data(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TRAVEL_NOTIFICATION_DB_DIR", str(tmp_path))
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("SEED_DEMO_DATA", raising=False)
    monkeypatch.setenv("BOOTSTRAP_ADMIN_USERNAME", "prod-admin")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "ProdPass123456")
    monkeypatch.setenv("NOTIFICATION_QUEUE_INTERVAL_SECONDS", "3600")
    from app.api.http import create_app

    app = create_app()
    ctx = app.state.ctx
    assert ctx.trip_repository.list() == []
    assert ctx.notification_rule_repository.list_rules(tenant_id="tenant-a") == []
    templates = ctx.template_service.list_notification_templates(tenant_id="tenant-a")
    assert len(templates) <= 1  # only the generic default template, no concierge demo set


def test_seed_demo_data_can_be_forced_in_production(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TRAVEL_NOTIFICATION_DB_DIR", str(tmp_path))
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SEED_DEMO_DATA", "true")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_USERNAME", "prod-admin")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "ProdPass123456")
    monkeypatch.setenv("NOTIFICATION_QUEUE_INTERVAL_SECONDS", "3600")
    from app.api.http import create_app

    app = create_app()
    ctx = app.state.ctx
    assert ctx.trip_repository.list()
    assert ctx.notification_rule_repository.list_rules(tenant_id="tenant-a")
    assert len(ctx.template_service.list_notification_templates(tenant_id="tenant-a")) > 1
