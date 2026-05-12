from __future__ import annotations

import gzip
import json

from app.modules.integration import weather_provider
from app.modules.integration.weather_provider import (
    QWeatherProvider,
    WeatherProvider,
    _default_qweather_transport,
)


def test_qweather_provider_normalizes_host_and_api_key_header() -> None:
    calls: list[dict[str, object]] = []

    def transport(
        host: str,
        path: str,
        params: dict[str, str],
        headers: dict[str, str],
    ) -> dict[str, object]:
        calls.append(
            {
                "host": host,
                "path": path,
                "params": params,
                "headers": headers,
            }
        )
        if path == "/geo/v2/city/lookup":
            return {
                "location": [
                    {
                        "id": "101010100",
                        "lat": "39.9042",
                        "lon": "116.4074",
                        "name": "北京",
                    }
                ]
            }
        if path == "/v7/weather/now":
            return {
                "updateTime": "2026-05-12T22:30+08:00",
                "fxLink": "https://example.com/weather/beijing",
                "now": {
                    "obsTime": "2026-05-12T22:25+08:00",
                    "temp": "26",
                    "feelsLike": "28",
                    "icon": "100",
                    "text": "晴",
                    "wind360": "180",
                    "windDir": "南风",
                    "windScale": "3",
                    "windSpeed": "12",
                    "humidity": "20",
                    "precip": "0.0",
                    "pressure": "1008",
                    "vis": "25",
                    "cloud": "5",
                    "dew": "1",
                },
                "refer": {
                    "sources": ["QWeather"],
                    "license": ["QWeather Developers License"],
                },
            }
        if path == "/v7/weather/24h":
            return {"hourly": []}
        if path == "/v7/weather/3d":
            return {
                "updateTime": "2026-05-12T22:30+08:00",
                "fxLink": "https://example.com/weather/beijing-3d",
                "daily": [
                    {
                        "fxDate": "2026-05-12",
                        "sunrise": "04:58",
                        "sunset": "19:22",
                        "moonrise": "18:01",
                        "moonset": "03:41",
                        "moonPhase": "盈凸月",
                        "moonPhaseIcon": "803",
                        "tempMax": "28",
                        "tempMin": "15",
                        "iconDay": "101",
                        "textDay": "多云",
                        "iconNight": "150",
                        "textNight": "晴",
                        "wind360Day": "180",
                        "windDirDay": "南风",
                        "windScaleDay": "3-4",
                        "windSpeedDay": "18",
                        "wind360Night": "0",
                        "windDirNight": "北风",
                        "windScaleNight": "1-2",
                        "windSpeedNight": "6",
                        "humidity": "40",
                        "precip": "0.0",
                        "pressure": "1008",
                        "vis": "24",
                        "cloud": "30",
                        "uvIndex": "6",
                    },
                    {
                        "fxDate": "2026-05-13",
                        "sunrise": "04:57",
                        "sunset": "19:23",
                        "moonrise": "19:02",
                        "moonset": "04:02",
                        "moonPhase": "盈凸月",
                        "moonPhaseIcon": "803",
                        "tempMax": "22",
                        "tempMin": "11",
                        "iconDay": "305",
                        "textDay": "小雨",
                        "iconNight": "306",
                        "textNight": "中雨",
                        "wind360Day": "90",
                        "windDirDay": "东风",
                        "windScaleDay": "4-5",
                        "windSpeedDay": "28",
                        "wind360Night": "90",
                        "windDirNight": "东风",
                        "windScaleNight": "3-4",
                        "windSpeedNight": "20",
                        "humidity": "76",
                        "precip": "12.5",
                        "pressure": "1001",
                        "vis": "10",
                        "cloud": "95",
                        "uvIndex": "2",
                    },
                ],
                "refer": {
                    "sources": ["QWeather", "ECMWF"],
                    "license": ["QWeather Developers License"],
                },
            }
        if path.startswith("/weatheralert/v1/current/"):
            return {"warning": []}
        raise AssertionError(f"Unexpected path: {path}")

    provider = QWeatherProvider(
        api_host="pt2mtfnnuq.re.qweatherapi.com",
        api_key="test-api-key",
        transport=transport,
    )

    weather = provider.get_weather("北京")

    assert weather.source == "qweather"
    assert weather.destination == "北京"
    assert weather.update_time == "2026-05-12T22:30+08:00"
    assert weather.obs_time == "2026-05-12T22:25+08:00"
    assert weather.feels_like == 28.0
    assert weather.icon == "100"
    assert weather.wind_degrees == 180
    assert weather.wind_direction == "南风"
    assert weather.wind_scale == "3"
    assert weather.wind_speed == 12.0
    assert weather.humidity == 20
    assert weather.precipitation == 0.0
    assert weather.pressure == 1008.0
    assert weather.visibility == 25.0
    assert weather.cloud == 5
    assert weather.dew_point == 1.0
    assert weather.fx_link == "https://example.com/weather/beijing"
    assert weather.refer_sources == ["QWeather"]
    assert weather.refer_license == ["QWeather Developers License"]
    assert len(weather.daily_forecast) == 2
    assert weather.daily_forecast[0]["fx_date"] == "2026-05-12"
    assert weather.daily_forecast[0]["temp_max"] == 28.0
    assert weather.daily_forecast[1]["text_day"] == "小雨"
    assert weather.daily_forecast[1]["precip"] == 12.5
    assert calls
    assert all(call["host"] == "https://pt2mtfnnuq.re.qweatherapi.com" for call in calls)
    assert all(call["headers"]["X-QW-Api-Key"] == "test-api-key" for call in calls)
    assert all(call["headers"]["Accept-Encoding"] == "gzip" for call in calls)


def test_default_qweather_transport_decompresses_gzip_response(
    monkeypatch,
) -> None:
    class DummyResponse:
        def __init__(self, body: bytes) -> None:
            self._body = body
            self.headers = {"Content-Encoding": "gzip"}

        def read(self) -> bytes:
            return self._body

        def __enter__(self) -> DummyResponse:
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout: int):
        headers = {key.lower(): value for key, value in request.header_items()}
        captured["url"] = request.full_url
        captured["accept_encoding"] = headers.get("accept-encoding")
        captured["api_key"] = headers.get("x-qw-api-key")
        captured["timeout"] = timeout
        body = gzip.compress(json.dumps({"code": "200", "now": {"text": "晴"}}).encode("utf-8"))
        return DummyResponse(body)

    monkeypatch.setenv("QWEATHER_API_HOST", "pt2mtfnnuq.re.qweatherapi.com")
    monkeypatch.setattr(weather_provider, "urlopen", fake_urlopen)

    payload = _default_qweather_transport(
        "https://pt2mtfnnuq.re.qweatherapi.com",
        "/v7/weather/now",
        {"location": "101010100"},
        {"Accept": "application/json", "Accept-Encoding": "gzip", "X-QW-Api-Key": "k"},
    )

    assert payload["code"] == "200"
    assert captured["url"] == (
        "https://pt2mtfnnuq.re.qweatherapi.com/v7/weather/now?location=101010100"
    )
    assert captured["accept_encoding"] == "gzip"
    assert captured["api_key"] == "k"
    assert captured["timeout"] == 5


def test_weather_provider_requires_qweather_credentials(monkeypatch) -> None:
    monkeypatch.delenv("QWEATHER_API_HOST", raising=False)
    monkeypatch.delenv("QWEATHER_API_KEY", raising=False)
    monkeypatch.setattr(weather_provider, "_load_local_env_file", lambda: None)

    provider = WeatherProvider()

    try:
        provider.get_weather("北京")
    except RuntimeError as exc:
        assert str(exc) == "QWEATHER_API_HOST and QWEATHER_API_KEY must be configured"
    else:
        raise AssertionError("Expected WeatherProvider to reject missing QWeather credentials")
