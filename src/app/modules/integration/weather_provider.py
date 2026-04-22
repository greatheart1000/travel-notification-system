from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

WeatherTransport = Callable[[str, dict[str, str], dict[str, str]], dict[str, Any]]


class WeatherAlertProvider(Protocol):
    def get_weather(
        self,
        destination: str,
        location_context: dict[str, Any] | None = None,
    ) -> WeatherInfo:
        """Fetch weather info for destination."""


@dataclass(slots=True)
class WeatherInfo:
    destination: str
    condition: str
    temperature: float
    warning_level: str | None = None
    alert_title: str = ""
    location_id: str = ""
    lat: str = ""
    lon: str = ""
    hourly_forecast: list[dict[str, Any]] = field(default_factory=list)
    daily_forecast: list[dict[str, Any]] = field(default_factory=list)
    alerts: list[dict[str, Any]] = field(default_factory=list)
    source: str = "mock"


def _normalize_warning_level(raw_title: str) -> str | None:
    title = raw_title.strip()
    if not title:
        return None
    mapping = {
        "红": "red",
        "橙": "orange",
        "黄": "yellow",
        "蓝": "blue",
    }
    for token, level in mapping.items():
        if token in title:
            return level
    lowered = title.lower()
    for token, level in (
        ("red", "red"),
        ("orange", "orange"),
        ("yellow", "yellow"),
        ("blue", "blue"),
    ):
        if token in lowered:
            return level
    return "warning"


def _default_qweather_transport(
    path: str, params: dict[str, str], headers: dict[str, str]
) -> dict[str, Any]:
    host = os.getenv("QWEATHER_API_HOST", "").strip().rstrip("/")
    if not host:
        raise RuntimeError("QWEATHER_API_HOST is not configured")

    query = urlencode(params)
    url = f"{host}{path}"
    if query:
        url = f"{url}?{query}"
    request = Request(url=url, headers=headers, method="GET")
    with urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def _load_local_env_file() -> None:
    env_path = Path.cwd() / ".env.local"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip("'").strip('"')


@dataclass(slots=True)
class MockWeatherProvider:
    def _deterministic_profile(self, destination: str) -> tuple[str, float, str | None]:
        # Keep mock output deterministic so risk analysis and copy generation are stable.
        normalized = destination.strip() or "default"
        score = sum(ord(ch) for ch in normalized)
        index = score % 5
        if index == 0:
            return "晴", 26.0, None
        if index == 1:
            return "多云", 21.0, None
        if index == 2:
            return "小雨", 18.0, "yellow"
        if index == 3:
            return "中雨", 15.0, "orange"
        return "雨夹雪", 2.0, "red"

    def get_weather(
        self,
        destination: str,
        location_context: dict[str, Any] | None = None,
    ) -> WeatherInfo:
        condition, temp, warning = self._deterministic_profile(destination)

        logger.info("Fetched mock weather for %s: %s, %sC", destination, condition, temp)
        return WeatherInfo(
            destination=destination,
            condition=condition,
            temperature=temp,
            warning_level=warning,
            alert_title=f"模拟天气{warning}级提醒" if warning else "",
            location_id=str((location_context or {}).get("qweather_location_id", "")),
            lat=str((location_context or {}).get("qweather_lat", "")),
            lon=str((location_context or {}).get("qweather_lon", "")),
            source="mock",
        )


@dataclass(slots=True)
class QWeatherProvider:
    api_host: str = ""
    api_key: str = ""
    transport: WeatherTransport = _default_qweather_transport

    def __post_init__(self) -> None:
        _load_local_env_file()
        if not self.api_host:
            self.api_host = os.getenv("QWEATHER_API_HOST", "").strip().rstrip("/")
        if not self.api_key:
            self.api_key = os.getenv("QWEATHER_API_KEY", "").strip()

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-QW-Api-Key"] = self.api_key
        return headers

    def _request(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        return self.transport(path, params, self._headers())

    def _resolve_location(self, destination: str) -> dict[str, str]:
        payload = self._request("/geo/v2/city/lookup", {"location": destination})
        location = (payload.get("location") or [{}])[0]
        return {
            "location_id": str(location.get("id", "")),
            "lat": str(location.get("lat", "")),
            "lon": str(location.get("lon", "")),
            "name": str(location.get("name", destination)),
        }

    def get_weather(
        self,
        destination: str,
        location_context: dict[str, Any] | None = None,
    ) -> WeatherInfo:
        context = location_context or {}
        location_id = str(
            context.get("qweather_location_id") or context.get("location_id") or ""
        ).strip()
        lat = str(context.get("qweather_lat") or context.get("lat") or "").strip()
        lon = str(context.get("qweather_lon") or context.get("lon") or "").strip()
        resolved_destination = destination

        if not location_id:
            resolved = self._resolve_location(destination)
            location_id = resolved["location_id"]
            lat = lat or resolved["lat"]
            lon = lon or resolved["lon"]
            resolved_destination = resolved["name"]

        now_payload = self._request("/v7/weather/now", {"location": location_id})
        hourly_payload = self._request("/v7/weather/24h", {"location": location_id})

        alert_path = f"/weatheralert/v1/current/{lat}/{lon}" if lat and lon else ""
        alerts = []
        if alert_path:
            alert_payload = self._request(alert_path, {})
            alerts = list(alert_payload.get("warning") or [])

        now = now_payload.get("now") or {}
        alert_title = str((alerts[0] or {}).get("title", "")) if alerts else ""
        return WeatherInfo(
            destination=resolved_destination,
            condition=str(now.get("text", "")),
            temperature=float(now.get("temp", 0.0) or 0.0),
            warning_level=_normalize_warning_level(alert_title),
            alert_title=alert_title,
            location_id=location_id,
            lat=lat,
            lon=lon,
            hourly_forecast=list(hourly_payload.get("hourly") or []),
            alerts=alerts,
            source="qweather",
        )


class WeatherProvider:
    def __init__(self) -> None:
        _load_local_env_file()
        host = os.getenv("QWEATHER_API_HOST", "").strip()
        api_key = os.getenv("QWEATHER_API_KEY", "").strip()
        host_configured = bool(host) and "__FILL_" not in host
        if host_configured and api_key:
            self.provider: WeatherAlertProvider = QWeatherProvider(
                api_host=host,
                api_key=api_key,
            )
        else:
            self.provider = MockWeatherProvider()

    def get_weather(
        self,
        destination: str,
        location_context: dict[str, Any] | None = None,
    ) -> WeatherInfo:
        return self.provider.get_weather(destination, location_context=location_context)
