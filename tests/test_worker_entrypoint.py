from __future__ import annotations


def test_worker_builds_scheduler_without_web_server(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TRAVEL_NOTIFICATION_DB_DIR", str(tmp_path))
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("NOTIFICATION_QUEUE_INTERVAL_SECONDS", "3600")

    from app.worker import build_worker_context

    context = build_worker_context()

    assert context.scheduler_service is not None
    assert context.weather_query_service is not None
