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


def test_trip_assignment_grants_guide_visibility_and_cleans_up(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TRAVEL_NOTIFICATION_DB_DIR", str(tmp_path))
    monkeypatch.setenv("NOTIFICATION_QUEUE_INTERVAL_SECONDS", "3600")
    from app.api.http import create_app

    app = create_app()
    with TestClient(app) as client:
        admin_token = _login(client, "admin")
        created_user = client.post(
            "/api/admin/users",
            headers=_auth(admin_token),
            json={
                "username": "guide-test",
                "password": "Guide123456",
                "role": "guide",
            },
        )
        assert created_user.status_code == 201, created_user.text
        guide_id = created_user.json()["data"]["id"]
        guide_token = _login(client, "guide-test", "Guide123456")

        created_trip = client.post(
            "/api/trips",
            headers=_auth(admin_token),
            json={
                "destination": "导游分配测试团",
                "team": "TEAM-GUIDE-ASSIGN",
                "start_date": "2026-12-01",
                "end_date": "2026-12-03",
                "participants": 2,
            },
        )
        assert created_trip.status_code == 201, created_trip.text
        trip_id = created_trip.json()["data"]["trip"]["id"]

        before = client.get("/api/trips", headers=_auth(guide_token))
        assert before.status_code == 200
        assert all(item["id"] != trip_id for item in before.json()["data"]["items"])
        denied = client.get(f"/api/trips/{trip_id}", headers=_auth(guide_token))
        assert denied.status_code == 403

        assigned = client.put(
            f"/api/trips/{trip_id}/assignments",
            headers=_auth(admin_token),
            json={"user_ids": [guide_id]},
        )
        assert assigned.status_code == 200, assigned.text
        assert assigned.json()["data"]["assigned_user_ids"] == [guide_id]
        assert [user["username"] for user in assigned.json()["data"]["users"]] == ["guide-test"]

        after = client.get("/api/trips", headers=_auth(guide_token))
        assert after.status_code == 200
        listed = [item for item in after.json()["data"]["items"] if item["id"] == trip_id]
        assert len(listed) == 1
        assert listed[0]["assigned_user_ids"] == [guide_id]
        assert listed[0]["assigned_users"][0]["username"] == "guide-test"

        detail = client.get(f"/api/trips/{trip_id}", headers=_auth(guide_token))
        assert detail.status_code == 200
        assert detail.json()["data"]["assigned_user_ids"] == [guide_id]
        assert detail.json()["data"]["assigned_users"][0]["username"] == "guide-test"

        guide_cannot_assign = client.put(
            f"/api/trips/{trip_id}/assignments",
            headers=_auth(guide_token),
            json={"user_ids": [guide_id]},
        )
        assert guide_cannot_assign.status_code == 403

        cross_tenant = client.put(
            f"/api/trips/{trip_id}/assignments",
            headers=_auth(admin_token),
            json={"user_ids": ["user-003"]},
        )
        assert cross_tenant.status_code == 400

        removed = client.delete(f"/api/trips/{trip_id}", headers=_auth(admin_token))
        assert removed.status_code == 200
        assert app.state.ctx.trip_assignment_repository.list_user_ids(trip_id, "tenant-a") == []
        assert client.get(f"/api/trips/{trip_id}", headers=_auth(guide_token)).status_code == 404


def test_unknown_assigned_user_is_rejected(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TRAVEL_NOTIFICATION_DB_DIR", str(tmp_path))
    monkeypatch.setenv("NOTIFICATION_QUEUE_INTERVAL_SECONDS", "3600")
    from app.api.http import create_app

    app = create_app()
    with TestClient(app) as client:
        admin_token = _login(client, "admin")
        created_trip = client.post(
            "/api/trips",
            headers=_auth(admin_token),
            json={
                "destination": "非法分配测试团",
                "team": "TEAM-GUIDE-INVALID",
                "start_date": "2026-12-05",
                "end_date": "2026-12-06",
                "participants": 1,
            },
        )
        trip_id = created_trip.json()["data"]["trip"]["id"]
        rejected = client.put(
            f"/api/trips/{trip_id}/assignments",
            headers=_auth(admin_token),
            json={"user_ids": ["does-not-exist"]},
        )
        assert rejected.status_code == 400
        assert "invalid_assigned_user_ids" in rejected.json()["error"]
