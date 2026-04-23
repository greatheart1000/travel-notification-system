from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.http import app, reset_state


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def test_workbench_overview_and_action_items() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)
    token = _login(client, "admin", "123456")
    headers = {"Authorization": f"Bearer {token}"}

    overview = client.get("/api/workbench/today/overview?owner_scope=all", headers=headers)
    assert overview.status_code == 200
    payload = overview.json()["data"]
    assert payload["pending_tasks"] >= 1
    assert payload["risky_trips"] >= 0

    action_items = client.get("/api/workbench/today/action-items?limit=5", headers=headers)
    assert action_items.status_code == 200
    items = action_items.json()["data"]["items"]
    assert len(items) >= 1
    assert "trip_id" in items[0]
    assert "node_key" in items[0]


def test_trip_execution_and_dispatch_workflow() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)
    token = _login(client, "admin", "123456")
    headers = {"Authorization": f"Bearer {token}"}

    rows_resp = client.get("/api/trips/execution?owner_scope=all", headers=headers)
    assert rows_resp.status_code == 200
    rows = rows_resp.json()["data"]["items"]
    assert len(rows) >= 1
    trip_id = rows[0]["trip_id"]

    detail_resp = client.get(f"/api/trips/{trip_id}/execution", headers=headers)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()["data"]
    assert detail["trip_id"] == trip_id
    assert len(detail["tasks"]) >= 1
    task_id = detail["tasks"][0]["task_id"]
    node_key = detail["tasks"][0]["node_key"]

    preview = client.post(
        "/api/notifications/dispatch/preview",
        headers=headers,
        json={"trip_id": trip_id, "node_key": node_key, "channel": "sms"},
    )
    assert preview.status_code == 200
    assert "content" in preview.json()["data"]

    dispatch = client.post(
        "/api/notifications/dispatch",
        headers=headers,
        json={"trip_id": trip_id, "node_key": node_key, "channel": "sms"},
    )
    assert dispatch.status_code == 200
    dispatch_data = dispatch.json()["data"]
    assert "dispatch_id" in dispatch_data

    retry = client.post(
        f"/api/notifications/dispatch/{dispatch_data['dispatch_id']}/retry",
        headers=headers,
        json={"reason": "manual retry from test"},
    )
    assert retry.status_code == 200
    assert retry.json()["data"]["status"] == "retrying"

    takeover = client.post(
        "/api/workbench/takeovers",
        headers=headers,
        json={
            "task_id": task_id,
            "assignee_user_id": "u-001",
            "assignee_name": "联调同学",
            "note": "handover test",
        },
    )
    assert takeover.status_code == 200
    assert takeover.json()["data"]["status"] == "handover_in_progress"

    complete = client.post(
        f"/api/workbench/tasks/{task_id}/complete",
        headers=headers,
        json={"result_note": "done from test", "evidence_type": "none"},
    )
    assert complete.status_code == 200
    assert complete.json()["data"]["status"] == "done"

    nudge = client.post(
        f"/api/workbench/tasks/{task_id}/nudge",
        headers=headers,
        json={"target_role": "guide", "message": "please follow up"},
    )
    assert nudge.status_code == 200
    assert nudge.json()["data"]["status"] == "nudged"
