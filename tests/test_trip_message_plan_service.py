from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from app.services.trip_message_plan_service import build_trip_message_plan


def _trip():
    return {
        "id": "trip-plan",
        "tenant_id": "tenant-a",
        "destination": "喀什",
        "start_date": "2026-11-15",
        "end_date": "2026-11-17",
        "itinerary": [
            {"date": "2026-11-15", "activity": "喀什老城", "hotel": "喀什酒店"},
            {"date": "2026-11-16", "activity": "帕米尔高原", "hotel": "塔县酒店"},
            {"date": "2026-11-17", "activity": "返程", "hotel": ""},
        ],
    }


def test_plan_covers_morning_noon_evening_and_next_day() -> None:
    plan = build_trip_message_plan(
        trip=_trip(),
        rules=[],
        template_service=SimpleNamespace(),
        attempts=[],
        today=date(2026, 11, 13),
    )

    assert len(plan) == 12
    titles = [item["title"] for item in plan]
    assert "行前准备提醒" in titles
    assert "行前最终确认" in titles
    assert titles.count("今日早间提醒") == 3
    assert titles.count("午间安全提醒") == 3
    assert titles.count("晚间次日预告") == 3
    assert plan[-1]["title"] == "行程回访"

    day2_morning = next(
        item
        for item in plan
        if item["date"] == "2026-11-16" and item["slot"] == "morning"
    )
    assert "帕米尔高原" in day2_morning["content"]
    assert "高原" in day2_morning["content"]
    day2_evening = next(
        item
        for item in plan
        if item["date"] == "2026-11-16" and item["slot"] == "evening"
    )
    assert "返程" in day2_evening["content"]


def test_plan_status_uses_attempts_and_past_dates() -> None:
    attempts = [
        {
            "attempted_at": "2026-11-16T07:05:00+08:00",
            "ok": True,
            "status": "sent",
        },
        {
            "attempted_at": "2026-11-16T12:31:00+08:00",
            "ok": False,
            "status": "failed",
        },
    ]
    plan = build_trip_message_plan(
        trip=_trip(),
        rules=[],
        template_service=SimpleNamespace(),
        attempts=attempts,
        today=date(2026, 11, 15),
    )
    by_key = {(item["date"], item["slot"]): item for item in plan}
    assert by_key[("2026-11-16", "morning")]["status"] == "sent"
    assert by_key[("2026-11-16", "afternoon")]["status"] == "failed"
    assert by_key[("2026-11-12", "morning")]["status"] == "missed"
    assert by_key[("2026-11-17", "morning")]["status"] == "pending"


def test_plan_uses_schedule_key_even_when_sent_late() -> None:
    plan = build_trip_message_plan(
        trip=_trip(),
        rules=[],
        template_service=SimpleNamespace(),
        attempts=[
            {
                "schedule_key": "trip-plan:2026-11-16:in_trip:morning",
                "attempted_at": "2026-11-16T15:10:00+08:00",
                "ok": True,
                "status": "sent",
            }
        ],
        today=date(2026, 11, 16),
    )
    morning = next(
        item
        for item in plan
        if item["date"] == "2026-11-16" and item["slot"] == "morning"
    )
    assert morning["status"] == "sent"
