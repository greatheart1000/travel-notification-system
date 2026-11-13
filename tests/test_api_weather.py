from __future__ import annotations

from fastapi.testclient import TestClient


def _create_app(monkeypatch, tmp_path):
    monkeypatch.setenv("TRAVEL_NOTIFICATION_DB_DIR", str(tmp_path))
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("NOTIFICATION_QUEUE_INTERVAL_SECONDS", "3600")
    from app.api.http import create_app

    return create_app()


def _login(client: TestClient) -> str:
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "123456"},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["access_token"]


def test_region_weather_returns_city_list(monkeypatch, tmp_path) -> None:
    app = _create_app(monkeypatch, tmp_path)
    with TestClient(app) as client:
        token = _login(client)
        response = client.get(
            "/api/weather/xinjiang",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["region"] == "xinjiang"
    assert data["source"] == "mock"
    assert data["degraded"] is True
    assert len(data["cities"]) == 8
    assert {"city", "temp", "weather", "wind", "warning", "source"} <= set(data["cities"][0])


def test_region_weather_rejects_unknown_region(monkeypatch, tmp_path) -> None:
    app = _create_app(monkeypatch, tmp_path)
    with TestClient(app) as client:
        token = _login(client)
        response = client.get(
            "/api/weather/not-a-region",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "region_not_supported"
