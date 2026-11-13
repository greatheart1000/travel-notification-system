from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import monotonic
from typing import Any

from app.modules.integration.weather_provider import (
    MockWeatherProvider,
    WeatherInfo,
    WeatherProvider,
)

# 当前产品面向新疆线路；后续可按 region 扩展为配置化城市目录。
REGION_CITIES: dict[str, list[str]] = {
    "xinjiang": ["乌鲁木齐", "喀什", "伊犁", "阿勒泰", "吐鲁番", "塔城", "库尔勒", "和田"],
}

WARNING_LABELS = {
    "red": "红色预警",
    "orange": "橙色预警",
    "yellow": "黄色预警",
    "blue": "蓝色预警",
}


class UnknownWeatherRegion(ValueError):
    pass


def _warning_text(info: WeatherInfo) -> str | None:
    if info.alert_title:
        return info.alert_title
    if info.warning_level:
        return WARNING_LABELS.get(info.warning_level, "天气预警")
    return None


def _wind_text(info: WeatherInfo) -> str:
    if info.wind_scale:
        return f"{info.wind_scale}级"
    return info.wind_direction or "—"


@dataclass(slots=True)
class WeatherQueryService:
    """Read-through weather query with a per-process TTL cache.

    The QWeather provider is attempted first; if credentials are absent or the
    provider fails, the deterministic mock provider is used so the trip page
    still renders. ``source`` is returned per city so the UI can disclose when
    data is mocked instead of silently pretending it is live.
    """

    provider: WeatherProvider
    mock_provider: MockWeatherProvider = field(default_factory=MockWeatherProvider)
    cache_ttl_seconds: int = 600
    _cache: dict[str, tuple[float, dict[str, Any]]] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        try:
            self.cache_ttl_seconds = int(
                os.getenv("WEATHER_CACHE_TTL_SECONDS", str(self.cache_ttl_seconds))
            )
        except ValueError:
            pass

    def list_region(
        self,
        region: str,
        *,
        location_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_region = region.strip().lower()
        cities = REGION_CITIES.get(normalized_region)
        if not cities:
            raise UnknownWeatherRegion(normalized_region)

        context = {
            key: value
            for key, value in (location_context or {}).items()
            if value not in (None, "")
        }
        cache_key = f"{normalized_region}:{json.dumps(context, sort_keys=True, default=str)}"
        now = monotonic()
        cached = self._cache.get(cache_key)
        if cached and now - cached[0] < max(self.cache_ttl_seconds, 0):
            return cached[1]

        items: list[dict[str, Any]] = []
        for city in cities:
            info: WeatherInfo
            source: str
            try:
                info = self.provider.get_weather(city, location_context=context)
                source = info.source or "qweather"
            except Exception:  # noqa: BLE001 - one city/provider failure must not break the list
                info = self.mock_provider.get_weather(city, location_context=context)
                source = "mock"

            items.append(
                {
                    "city": info.destination or city,
                    "temp": round(float(info.temperature), 1),
                    "weather": info.condition or "未知",
                    "wind": _wind_text(info),
                    "warning": _warning_text(info),
                    "source": source,
                    "updated_at": info.update_time or info.obs_time or "",
                }
            )

        live_count = sum(1 for item in items if item["source"] == "qweather")
        result = {
            "region": normalized_region,
            "cities": items,
            "source": "qweather" if live_count == len(items) else "mock" if live_count == 0 else "mixed",
            "degraded": live_count < len(items),
            "updated_at": datetime.now(tz=UTC).isoformat(),
        }
        self._cache[cache_key] = (now, result)
        return result
