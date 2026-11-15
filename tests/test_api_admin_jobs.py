from __future__ import annotations

from fastapi.testclient import TestClient


def _login(client: TestClient, username: str) -> str:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": "123456"},
    )
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def test_admin_can_list_notification_jobs_and_partner_cannot(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TRAVEL_NOTIFICATION_DB_DIR", str(tmp_path))
    monkeypatch.setenv("NOTIFICATION_QUEUE_INTERVAL_SECONDS", "3600")
    from app.api.http import create_app

    app = create_app()
    with TestClient(app) as client:
        admin_token = _login(client, "admin")
        partner_token = _login(client, "partner")

        admin_response = client.get(
            "/api/admin/notification-jobs",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        partner_response = client.get(
            "/api/admin/notification-jobs",
            headers={"Authorization": f"Bearer {partner_token}"},
        )

    assert admin_response.status_code == 200
    assert admin_response.json()["data"]["items"] == []
    assert partner_response.status_code == 403
