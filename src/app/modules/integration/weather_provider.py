from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from gzip import decompress
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

WeatherTransport = Callable[[str, str, dict[str, str], dict[str, str]], dict[str, Any]]


class WeatherAlertProvider(Protocol):
    def get_weather(
        self,
        destination: str,
        location_context: dict[str, Any] | None = None,
        *,
        include_forecast: bool = True,
    ) -> WeatherInfo:
        """Fetch weather info for destination."""


@dataclass(slots=True)
class WeatherInfo:
    destination: str
    condition: str
    temperature: float
    update_time: str = ""
    obs_time: str = ""
    feels_like: float | None = None
    icon: str = ""
    wind_degrees: int | None = None
    wind_direction: str = ""
    wind_scale: str = ""
    wind_speed: float | None = None
    humidity: int | None = None
    precipitation: float | None = None
    pressure: float | None = None
    visibility: float | None = None
    cloud: int | None = None
    dew_point: float | None = None
    fx_link: str = ""
    refer_sources: list[str] = field(default_factory=list)
    refer_license: list[str] = field(default_factory=list)
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


def _to_float(raw: Any) -> float | None:
    if raw in (None, ""):
        return None
    return float(raw)


def _to_int(raw: Any) -> int | None:
    if raw in (None, ""):
        return None
    return int(raw)


def _normalize_daily_forecast(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "fx_date": str(item.get("fxDate", "")),
        "sunrise": str(item.get("sunrise", "")),
        "sunset": str(item.get("sunset", "")),
        "moonrise": str(item.get("moonrise", "")),
        "moonset": str(item.get("moonset", "")),
        "moon_phase": str(item.get("moonPhase", "")),
        "moon_phase_icon": str(item.get("moonPhaseIcon", "")),
        "temp_max": _to_float(item.get("tempMax")),
        "temp_min": _to_float(item.get("tempMin")),
        "icon_day": str(item.get("iconDay", "")),
        "text_day": str(item.get("textDay", "")),
        "icon_night": str(item.get("iconNight", "")),
        "text_night": str(item.get("textNight", "")),
        "wind360_day": _to_int(item.get("wind360Day")),
        "wind_dir_day": str(item.get("windDirDay", "")),
        "wind_scale_day": str(item.get("windScaleDay", "")),
        "wind_speed_day": _to_float(item.get("windSpeedDay")),
        "wind360_night": _to_int(item.get("wind360Night")),
        "wind_dir_night": str(item.get("windDirNight", "")),
        "wind_scale_night": str(item.get("windScaleNight", "")),
        "wind_speed_night": _to_float(item.get("windSpeedNight")),
        "humidity": _to_int(item.get("humidity")),
        "precip": _to_float(item.get("precip")),
        "pressure": _to_float(item.get("pressure")),
        "visibility": _to_float(item.get("vis")),
        "cloud": _to_int(item.get("cloud")),
        "uv_index": _to_int(item.get("uvIndex")),
    }


def _default_qweather_transport(
    host: str, path: str, params: dict[str, str], headers: dict[str, str]
) -> dict[str, Any]:
    import gzip as gzip_module
    raw_host = host or os.getenv("QWEATHER_API_HOST", "")
    host = _normalize_qweather_host(raw_host)
    if not host:
        raise RuntimeError("QWEATHER_API_HOST is not configured")

    from urllib.parse import quote
    encoded_pairs = [(k, quote(str(v), safe='')) for k, v in params.items()]
    query = urlencode(encoded_pairs)
    url = f"{host}{path}"
    if query:
        url = f"{url}?{query}"
    request = Request(url=url, headers=headers, method="GET")
    with urlopen(request, timeout=5) as response:
        raw = response.read()
        # 处理 gzip 压缩响应
        if raw[:2] == b'\x1f\x8b':
            raw = gzip_module.decompress(raw)
        return json.loads(raw.decode("utf-8"))


def _load_local_env_file() -> None:
    # 从项目根目录加载
    env_path = Path(__file__).resolve().parent.parent.parent.parent.parent / ".env.local"
    if not env_path.exists():
        # 兼容旧路径
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


def _normalize_qweather_host(raw_host: str) -> str:
    host = raw_host.strip()
    if not host:
        return ""
    if not host.startswith(("http://", "https://")):
        host = f"https://{host}"
    return host.rstrip("/")


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
        *,
        include_forecast: bool = True,
    ) -> WeatherInfo:
        condition, temp, warning = self._deterministic_profile(destination)

        warning_labels = {
            "yellow": "黄色预警",
            "orange": "橙色预警",
            "red": "红色预警",
            "blue": "蓝色预警",
        }
        logger.info("Fetched mock weather for %s: %s, %sC", destination, condition, temp)
        return WeatherInfo(
            destination=destination,
            condition=condition,
            temperature=temp,
            warning_level=warning,
            alert_title=warning_labels.get(warning or "", "") if warning else "",
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
            self.api_host = os.getenv("QWEATHER_API_HOST", "")
        self.api_host = _normalize_qweather_host(self.api_host)
        if not self.api_key:
            self.api_key = os.getenv("QWEATHER_API_KEY", "").strip()

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "Accept-Encoding": "gzip"}
        if self.api_key:
            headers["X-QW-Api-Key"] = self.api_key
        return headers

    def _request(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        return self.transport(self.api_host, path, params, self._headers())

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
        *,
        include_forecast: bool = True,
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
        hourly_payload = (
            self._request("/v7/weather/24h", {"location": location_id})
            if include_forecast
            else {}
        )
        daily_payload = (
            self._request("/v7/weather/3d", {"location": location_id})
            if include_forecast
            else {}
        )

        alert_path = f"/weatheralert/v1/current/{lat}/{lon}" if lat and lon else ""
        alerts: list[dict[str, Any]] = []
        if alert_path:
            try:
                alert_payload = self._request(alert_path, {})
                # QWeather v1 uses "alerts"; older payloads used "warning".
                alerts = list(alert_payload.get("alerts") or alert_payload.get("warning") or [])
            except Exception as exc:  # noqa: BLE001 - alerts are optional
                logger.warning(
                    "QWeather alert lookup failed for %s: %s", destination, type(exc).__name__
                )

        now = now_payload.get("now") or {}
        refer = now_payload.get("refer") or {}
        first_alert = alerts[0] if alerts else {}
        alert_title = str(first_alert.get("title") or first_alert.get("headline") or "")
        alert_color = str((first_alert.get("color") or {}).get("code") or "")
        warning_level = _normalize_warning_level(alert_title)
        if not warning_level and alert_color in {"blue", "yellow", "orange", "red"}:
            warning_level = alert_color
        return WeatherInfo(
            destination=resolved_destination,
            condition=str(now.get("text", "")),
            temperature=float(now.get("temp", 0.0) or 0.0),
            update_time=str(now_payload.get("updateTime", "")),
            obs_time=str(now.get("obsTime", "")),
            feels_like=_to_float(now.get("feelsLike")),
            icon=str(now.get("icon", "")),
            wind_degrees=_to_int(now.get("wind360")),
            wind_direction=str(now.get("windDir", "")),
            wind_scale=str(now.get("windScale", "")),
            wind_speed=_to_float(now.get("windSpeed")),
            humidity=_to_int(now.get("humidity")),
            precipitation=_to_float(now.get("precip")),
            pressure=_to_float(now.get("pressure")),
            visibility=_to_float(now.get("vis")),
            cloud=_to_int(now.get("cloud")),
            dew_point=_to_float(now.get("dew")),
            fx_link=str(now_payload.get("fxLink", "")),
            refer_sources=[str(item) for item in list(refer.get("sources") or [])],
            refer_license=[str(item) for item in list(refer.get("license") or [])],
            warning_level=warning_level,
            alert_title=alert_title,
            location_id=location_id,
            lat=lat,
            lon=lon,
            hourly_forecast=list(hourly_payload.get("hourly") or []),
            daily_forecast=[
                _normalize_daily_forecast(item)
                for item in list(daily_payload.get("daily") or [])
                if isinstance(item, dict)
            ],
            alerts=alerts,
            source="qweather",
        )


class WeatherProvider:
    def __init__(self) -> None:
        _load_local_env_file()
        self.provider: WeatherAlertProvider | None = None

    def _provider(self) -> WeatherAlertProvider:
        if self.provider is not None:
            return self.provider
        host = _normalize_qweather_host(os.getenv("QWEATHER_API_HOST", ""))
        api_key = os.getenv("QWEATHER_API_KEY", "").strip()
        host_configured = bool(host) and "__FILL_" not in host
        if not host_configured or not api_key:
            raise RuntimeError("QWEATHER_API_HOST and QWEATHER_API_KEY must be configured")
        self.provider = QWeatherProvider(
            api_host=host,
            api_key=api_key,
        )
        return self.provider

    def get_weather(
        self,
        destination: str,
        location_context: dict[str, Any] | None = None,
        *,
        include_forecast: bool = True,
    ) -> WeatherInfo:
        return self._provider().get_weather(
            destination,
            location_context=location_context,
            include_forecast=include_forecast,
        )
