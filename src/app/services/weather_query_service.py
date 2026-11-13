from __future__ import annotations

import json
import os
import re
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

# QWeather location ids/coordinates for the fixed region list. Using ids avoids
# one geo lookup per city; coordinates are needed for the alert endpoint.
REGION_CITY_LOCATIONS: dict[str, dict[str, dict[str, str]]] = {
    "xinjiang": {
        "乌鲁木齐": {"id": "101130101", "lat": "43.79282", "lon": "87.61773"},
        "喀什": {"id": "101130901", "lat": "39.46766", "lon": "75.98914"},
        "伊犁": {"id": "101131012", "lat": "43.92186", "lon": "81.31795"},
        "阿勒泰": {"id": "101131401", "lat": "47.84891", "lon": "88.13874"},
        "吐鲁番": {"id": "101130501", "lat": "42.94761", "lon": "89.18407"},
        "塔城": {"id": "101131101", "lat": "46.74628", "lon": "82.98399"},
        "库尔勒": {"id": "101130601", "lat": "41.76312", "lon": "86.14595"},
        "和田": {"id": "101131301", "lat": "37.10894", "lon": "79.92754"},
    },
}

WARNING_LABELS = {
    "red": "红色预警",
    "orange": "橙色预警",
    "yellow": "黄色预警",
    "blue": "蓝色预警",
}


class UnknownWeatherRegion(ValueError):
    pass


def _short_warning(title: str) -> str | None:
    """Turn a full alert headline into the short badge text.

    QWeather returns headlines such as
    ``新疆维吾尔自治区气象台发布暴雪蓝色预警``; the badge should read
    ``暴雪蓝色预警`` while the full headline stays available as a tooltip.
    """
    headline = (title or "").strip()
    if not headline:
        return None
    match = re.search(r"(?:发布|更新)(.+?预警)$", headline)
    return match.group(1).strip() if match else headline


def _warning_fields(info: WeatherInfo) -> tuple[str | None, str | None]:
    if info.alert_title:
        return _short_warning(info.alert_title), info.alert_title
    if info.warning_level:
        return WARNING_LABELS.get(info.warning_level, "天气预警"), ""
    return None, ""


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
    cache_ttl_seconds: int = 1800
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
        region_locations = REGION_CITY_LOCATIONS.get(normalized_region, {})
        for city in cities:
            city_context = {
                key: value
                for key, value in context.items()
                if key not in {"qweather_location_id", "qweather_lat", "qweather_lon", "lat", "lon"}
            }
            city_location = region_locations.get(city) or {}
            if city_location:
                city_context["qweather_location_id"] = city_location["id"]
                city_context["qweather_lat"] = city_location["lat"]
                city_context["qweather_lon"] = city_location["lon"]
            info: WeatherInfo
            source: str
            try:
                info = self.provider.get_weather(
                    city,
                    location_context=city_context,
                    include_forecast=False,
                )
                source = info.source or "qweather"
            except Exception:  # noqa: BLE001 - one city/provider failure must not break the list
                info = self.mock_provider.get_weather(
                    city,
                    location_context=city_context,
                    include_forecast=False,
                )
                source = "mock"

            warning, warning_title = _warning_fields(info)
            items.append(
                {
                    "city": info.destination or city,
                    "temp": round(float(info.temperature), 1),
                    "weather": info.condition or "未知",
                    "wind": _wind_text(info),
                    "warning": warning,
                    "warning_title": warning_title,
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
