from __future__ import annotations

import pytest

from app.modules.integration.weather_provider import WeatherInfo
from app.services.weather_query_service import UnknownWeatherRegion, WeatherQueryService


class _FakeLiveProvider:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls = 0

    def get_weather(self, destination: str, location_context=None) -> WeatherInfo:
        self.calls += 1
        if self.fail:
            raise RuntimeError("weather upstream unavailable")
        return WeatherInfo(
            destination=destination,
            condition="晴",
            temperature=21.6,
            warning_level="yellow",
            alert_title="",
            wind_scale="3",
            source="qweather",
        )


def test_list_region_maps_live_weather_fields() -> None:
    provider = _FakeLiveProvider()
    service = WeatherQueryService(provider=provider, cache_ttl_seconds=0)

    result = service.list_region("xinjiang")

    assert result["region"] == "xinjiang"
    assert result["source"] == "qweather"
    assert result["degraded"] is False
    assert len(result["cities"]) == 8
    first = result["cities"][0]
    assert first["city"] == "乌鲁木齐"
    assert first["temp"] == 21.6
    assert first["weather"] == "晴"
    assert first["wind"] == "3级"
    assert first["warning"] == "黄色预警"
    assert first["source"] == "qweather"


def test_list_region_falls_back_to_mock_when_provider_fails() -> None:
    service = WeatherQueryService(provider=_FakeLiveProvider(fail=True), cache_ttl_seconds=0)

    result = service.list_region("xinjiang")

    assert result["source"] == "mock"
    assert result["degraded"] is True
    assert len(result["cities"]) == 8
    assert all(city["source"] == "mock" for city in result["cities"])
    warnings = [city["warning"] for city in result["cities"]]
    assert any(warnings)
    assert all(
        warning is None
        or warning in {"黄色预警", "橙色预警", "红色预警", "蓝色预警"}
        for warning in warnings
    )


def test_list_region_uses_ttl_cache() -> None:
    provider = _FakeLiveProvider()
    service = WeatherQueryService(provider=provider, cache_ttl_seconds=600)

    first = service.list_region("xinjiang")
    second = service.list_region("xinjiang")

    assert first == second
    assert provider.calls == 8


def test_unknown_region_is_rejected() -> None:
    service = WeatherQueryService(provider=_FakeLiveProvider(), cache_ttl_seconds=0)

    with pytest.raises(UnknownWeatherRegion):
        service.list_region("unknown-region")
