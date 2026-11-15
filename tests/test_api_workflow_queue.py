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


def test_workflow_failure_is_localized_and_enqueued(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TRAVEL_NOTIFICATION_DB_DIR", str(tmp_path))
    monkeypatch.setenv("NOTIFICATION_QUEUE_INTERVAL_SECONDS", "3600")
    monkeypatch.setenv("WECHAT_WEBHOOK_URL", "")
    from app.api.http import create_app

    app = create_app()
    with TestClient(app) as client:
        admin_token = _login(client, "admin")
        created = client.post(
            "/api/trips",
            headers=_auth(admin_token),
            json={
                "destination": "工作流失败入队测试团",
                "team": "TEAM-WORKFLOW-QUEUE",
                "start_date": "2026-12-10",
                "end_date": "2026-12-12",
                "participants": 1,
            },
        )
        trip_id = created.json()["data"]["trip"]["id"]

        executed = client.post(
            f"/api/trips/{trip_id}/workflow/execute?step=pre_flight_notice",
            headers=_auth(admin_token),
            json={},
        )
        assert executed.status_code == 502, executed.text
        message = executed.json()["error"]
        assert "企业微信未配置" in message
        assert "发送任务队列" in message
        assert "job-" in message

        jobs = client.get("/api/admin/notification-jobs", headers=_auth(admin_token))
        assert jobs.status_code == 200
        items = jobs.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["trip_id"] == trip_id
        assert items[0]["status"] == "manual_intervention"
        assert items[0]["channel"] == "wechat_work_group"
        assert items[0]["last_error"] == "wechat_webhook_not_configured"

        requeued = client.post(
            f"/api/admin/notification-jobs/{items[0]['job_id']}/requeue",
            headers=_auth(admin_token),
        )
        assert requeued.status_code == 200
        assert requeued.json()["data"]["status"] == "pending"
