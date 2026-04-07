from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import URLError
from urllib.request import Request, urlopen


@dataclass(slots=True)
class YituApiAdapter:
    """易途 API 适配器：未配置 base_url 时返回 stub。"""

    base_url: str = ""
    api_key: str = ""
    timeout_sec: int = 3

    def fetch_team_itinerary(self, team_id: str) -> dict:
        if not self.base_url:
            return {"team_id": team_id, "status": "stub", "itinerary": []}

        request = Request(
            url=f"{self.base_url.rstrip('/')}/teams/{team_id}/itinerary",
            headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {},
            method="GET",
        )
        try:
            with urlopen(request, timeout=self.timeout_sec) as response:
                return json.loads(response.read().decode("utf-8"))
        except (URLError, TimeoutError, json.JSONDecodeError):
            return {"team_id": team_id, "status": "fallback", "itinerary": []}


@dataclass(slots=True)
class WeatherAdapter:
    base_url: str = ""
    api_key: str = ""
    timeout_sec: int = 3

    def fetch_weather_tags(self, city_code: str) -> dict:
        if not self.base_url:
            return {
                "city_code": city_code,
                "rain": False,
                "uv": "medium",
                "cold_wave": False,
            }

        request = Request(
            url=f"{self.base_url.rstrip('/')}/weather/{city_code}",
            headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {},
            method="GET",
        )
        try:
            with urlopen(request, timeout=self.timeout_sec) as response:
                raw = json.loads(response.read().decode("utf-8"))
                return {
                    "city_code": city_code,
                    "rain": bool(raw.get("rain")),
                    "uv": raw.get("uv", "medium"),
                    "cold_wave": bool(raw.get("cold_wave")),
                }
        except (URLError, TimeoutError, json.JSONDecodeError):
            return {
                "city_code": city_code,
                "rain": False,
                "uv": "medium",
                "cold_wave": False,
            }
