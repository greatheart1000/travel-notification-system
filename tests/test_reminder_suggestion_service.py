from __future__ import annotations

import asyncio
from datetime import date

from app.modules.integration.weather_provider import WeatherInfo
from app.services.reminder_suggestion_service import (
    detect_suggestion,
    generate_reminder_suggestion,
    region_guidance,
)


def _trip(**overrides):
    payload = {
        "id": "trip-1",
        "tenant_id": "tenant-a",
        "destination": "喀纳斯",
        "start_date": "2026-11-20",
        "end_date": "2026-11-23",
        "itinerary": [
            {
                "date": "2026-11-20",
                "type": "商务车",
                "activity": "喀纳斯景区游览",
                "hotel": "湖区酒店",
            }
        ],
        "scene_tags": [],
    }
    payload.update(overrides)
    return payload


def test_region_guidance_differs_by_destination() -> None:
    assert "保暖" in region_guidance("喀纳斯")
    assert "防晒" in region_guidance("吐鲁番")
    assert "高原" in region_guidance("塔县")
    assert "外套" in region_guidance("未知目的地")


def test_pre_trip_suggestion_uses_destination_guidance() -> None:
    suggestion = detect_suggestion(
        _trip(), today=date(2026, 11, 18)
    )
    assert suggestion is not None
    assert suggestion["situation"] == "pre_trip"
    assert "还有 2 天" in suggestion["reason"]
    assert "喀纳斯" in suggestion["content"]
    assert "保暖" in suggestion["content"]


def test_in_trip_suggestion_uses_today_itinerary_and_region() -> None:
    suggestion = detect_suggestion(
        _trip(destination="吐鲁番"), today=date(2026, 11, 21)
    )
    assert suggestion is not None
    assert suggestion["situation"] == "in_trip"
    assert "防晒" in suggestion["content"]


def test_weather_warning_has_priority() -> None:
    weather = WeatherInfo(
        destination="喀纳斯",
        condition="暴雪",
        temperature=-12.0,
        warning_level="orange",
        alert_title="暴雪橙色预警",
    )
    suggestion = detect_suggestion(_trip(), weather, today=date(2026, 11, 21))
    assert suggestion is not None
    assert suggestion["situation"] == "weather_alert"
    assert "暴雪橙色预警" in suggestion["reason"]
    assert "暴雪" in suggestion["content"]
    assert len(suggestion["variants"]) == 2
    assert suggestion["variants"][0]["title"] == "游客群通知"
    assert suggestion["variants"][1]["title"] == "内部协同提醒"
    assert "防滑链" in suggestion["variants"][1]["content"]
    assert suggestion["suggested_actions"]


def test_special_scene_tag_changes_suggestion() -> None:
    suggestion = detect_suggestion(
        _trip(scene_tags=["骑马"]), today=date(2026, 11, 21)
    )
    assert suggestion is not None
    assert suggestion["situation"] == "special_scene"
    assert "骑马" in suggestion["title"]
    assert "护具" in suggestion["content"]


def test_far_future_trip_has_no_immediate_suggestion() -> None:
    assert detect_suggestion(_trip(), today=date(2026, 11, 1)) is None


def test_generate_suggestion_uses_local_polish_without_key(monkeypatch) -> None:
    monkeypatch.delenv("GLM_API_KEY", raising=False)
    result = asyncio.run(
        generate_reminder_suggestion(_trip(), today=date(2026, 11, 18))
    )
    assert result is not None
    assert result["provider"] == "local"
    assert result["content"]
    assert result["generated_at"]
