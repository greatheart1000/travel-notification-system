from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.core.entities import Channel, DeliveryStatus, DomainEvent, EventName
from app.main import bootstrap_demo, build_app


def test_bootstrap_demo_success() -> None:
    result = bootstrap_demo()
    assert result["published"] == 1
    assert result["status"] is True


def test_fallback_channel_when_push_failed() -> None:
    bff, dispatch, bus = build_app(fail_push_once=True)
    bff.create_trip("T-1", "U-1", "Xinjiang", datetime(2026, 6, 1, tzinfo=timezone.utc))
    bff.update_preference("U-1", [Channel.PUSH, Channel.EMAIL], (1, 2))
    bff.upsert_rule(EventName.TRIP_CREATED, 1, [Channel.PUSH, Channel.EMAIL], max_per_hour=2)
    bff.upsert_template("tpl", EventName.TRIP_CREATED, "zh", 1, "hello {{trip_id}}", "A")

    event = DomainEvent(str(uuid4()), EventName.TRIP_CREATED, "T-1", "U-1")
    bff.ingest_event(event)
    bus.flush_outbox()

    assert dispatch.records[-1].status == DeliveryStatus.SUCCESS
    assert dispatch.records[-1].channel == Channel.EMAIL


def test_idempotent_same_event_only_once() -> None:
    bff, dispatch, bus = build_app()
    bff.create_trip("T-2", "U-2", "Xinjiang", datetime(2026, 6, 1, tzinfo=timezone.utc))
    bff.update_preference("U-2", [Channel.EMAIL], (1, 2))
    bff.upsert_rule(EventName.TRIP_CREATED, 1, [Channel.EMAIL], max_per_hour=2)
    bff.upsert_template("tpl2", EventName.TRIP_CREATED, "zh", 1, "hello {{trip_id}}", "A")

    event_id = str(uuid4())
    bff.ingest_event(DomainEvent(event_id, EventName.TRIP_CREATED, "T-2", "U-2"))
    bff.ingest_event(DomainEvent(event_id, EventName.TRIP_CREATED, "T-2", "U-2"))
    bus.flush_outbox()

    success = [r for r in dispatch.records if r.status == DeliveryStatus.SUCCESS]
    assert len(success) == 1
