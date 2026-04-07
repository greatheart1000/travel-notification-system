from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class YituApiAdapter:
    """易途 API 适配器占位。"""

    def fetch_team_itinerary(self, team_id: str) -> dict:
        return {"team_id": team_id, "status": "stub", "itinerary": []}


@dataclass(slots=True)
class WeatherAdapter:
    def fetch_weather_tags(self, city_code: str) -> dict:
        return {
            "city_code": city_code,
            "rain": False,
            "uv": "medium",
            "cold_wave": False,
        }
