from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.models import Channel
from app.core.observability import metrics, set_trace_id
from app.modules.notification.models import NotificationTask
from app.modules.notification.service import NotificationService
from tests.fakes import FakeChannelProvider


def _task() -> NotificationTask:
    return NotificationTask(
        tenant_id="tenant-a",
        team_id="team-1",
        trip_id="trip-1",
        customer_id="13800138000",
        rendered_content="hello",
        primary_channel=Channel.SMS,
        fallback_channel=None,
        idempotency_key="trace:tenant-a:trip-1:1",
        max_retry=1,
    )


def test_dispatch_propagates_trace_id_and_records_metrics() -> None:
    metrics.reset()
    set_trace_id("trace-test-1")
    service = NotificationService(
        providers={Channel.SMS: FakeChannelProvider(default=(True, "ok"))}
    )
    task = _task()

    service.dispatch(task)

    assert task.trace_id == "trace-test-1"
    assert task.attempts[0].trace_id == "trace-test-1"
    snapshot = metrics.snapshot()
    assert snapshot["counters"]["notification_send_attempts_total"] >= 1
    assert snapshot["counters"]["notification_send_success_total"] >= 1


def test_http_trace_header_is_echoed(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TRAVEL_NOTIFICATION_DB_DIR", str(tmp_path))
    monkeypatch.setenv("NOTIFICATION_QUEUE_INTERVAL_SECONDS", "3600")
    from app.api.http import create_app

    app = create_app()
    with TestClient(app) as client:
        response = client.get("/api/health", headers={"X-Trace-Id": "trace-http-1"})

    assert response.status_code == 200
    assert response.headers["X-Trace-Id"] == "trace-http-1"


def test_metrics_endpoint_returns_snapshot(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TRAVEL_NOTIFICATION_DB_DIR", str(tmp_path))
    monkeypatch.setenv("NOTIFICATION_QUEUE_INTERVAL_SECONDS", "3600")
    from app.api.http import create_app

    app = create_app()
    with TestClient(app) as client:
        response = client.get("/api/health/metrics")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert "counters" in body["data"]
