from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RiskResponseLevel(str, Enum):
    AUTO_SENT = "auto_sent"
    MANAGER_CONFIRMED = "manager_confirmed"
    MANAGEMENT_ESCALATED = "management_escalated"


@dataclass(slots=True)
class RiskSignal:
    weather: str
    road_status: str
    temperature: float
    wind_scale: int
    unresolved_minutes: int = 0


@dataclass(slots=True)
class RiskAlert:
    level: str
    hit_rules: list[str]
    recommendation_actions: list[str]
    response_level: RiskResponseLevel


class RiskAlertService:
    """天气与路况风险预警，含三级响应策略。"""

    def evaluate(self, signal: RiskSignal) -> RiskAlert | None:
        hit_rules: list[str] = []
        actions: list[str] = []

        if signal.weather in {"rain", "snow"}:
            hit_rules.append("precipitation")
            actions.append("建议准备雨衣/防滑链并提前发送防滑提醒")
        if signal.temperature <= -15:
            hit_rules.append("extreme_cold")
            actions.append("建议增加防寒提醒并核查保暖物资")
        if signal.wind_scale >= 7:
            hit_rules.append("strong_wind")
            actions.append("建议减少户外停留时长并准备替代点位")
        if signal.road_status in {"closed", "congested"}:
            hit_rules.append("road_condition")
            actions.append("建议提前发车并准备替代景点方案")

        if not hit_rules:
            return None

        if signal.unresolved_minutes >= 15:
            response_level = RiskResponseLevel.MANAGEMENT_ESCALATED
        elif signal.unresolved_minutes >= 5:
            response_level = RiskResponseLevel.MANAGER_CONFIRMED
        else:
            response_level = RiskResponseLevel.AUTO_SENT

        level = "critical" if len(hit_rules) >= 2 else "high"
        return RiskAlert(
            level=level,
            hit_rules=hit_rules,
            recommendation_actions=actions,
            response_level=response_level,
        )
