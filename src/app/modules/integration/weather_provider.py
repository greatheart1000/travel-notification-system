from __future__ import annotations

import logging
import random
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class WeatherInfo:
    destination: str
    condition: str  # e.g., "Rain", "Sunny", "Snow"
    temperature: float
    warning_level: str | None = None  # e.g., "Yellow", "Red"


class WeatherProvider:
    def get_weather(self, destination: str) -> WeatherInfo:
        # MVP 阶段模拟获取天气逻辑
        conditions = ["Sunny", "Cloudy", "Rain", "Snow", "Windy"]
        # 随机模拟：为了演示触发，有 30% 概率触发雨雪
        weights = [0.4, 0.3, 0.15, 0.1, 0.05]
        condition = random.choices(conditions, weights=weights)[0]

        temp = round(random.uniform(-5, 35), 1)
        warning = "Yellow" if condition in ["Rain", "Snow"] else None

        logger.info(f"Fetched mock weather for {destination}: {condition}, {temp}C")
        return WeatherInfo(
            destination=destination, condition=condition, temperature=temp, warning_level=warning
        )
