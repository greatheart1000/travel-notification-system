from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


RISK_KEYWORDS: dict[str, set[str]] = {
    "horse_riding": {"骑马", "马术"},
    "skiing": {"滑雪", "雪场"},
    "highland": {"高原", "海拔"},
    "border": {"边境", "口岸"},
    "extreme_uv": {"强紫外线", "暴晒"},
    "long_transfer": {"长途", "赶路", "车程", "转场"},
    "early_checkout": {"早起", "退房", "凌晨"},
}


@dataclass(slots=True)
class ItineraryItem:
    day: str
    title: str
    description: str
    distance_km: int = 0
    estimated_drive_hours: float = 0.0


@dataclass(slots=True)
class RushDayValidation:
    is_rush_day: bool
    passed: bool
    missing_items: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ItineraryRiskReport:
    risk_tags: set[str]
    rush_day_validation: RushDayValidation


class ItineraryRiskService:
    """解析行程并识别风险标签，支持赶路日强校验。"""

    RUSH_DAY_REQUIRED_KEYS: dict[str, str] = {
        "breakfast_packed": "早餐打包",
        "meeting_time_confirmed": "集合时间确认",
        "vehicle_buffer_checked": "用车余量检查",
        "critical_resource_ready": "关键资源准备",
    }

    def detect_risk_tags(self, items: Iterable[ItineraryItem]) -> set[str]:
        tags: set[str] = set()
        for item in items:
            full_text = f"{item.title} {item.description}".lower()
            for tag, keywords in RISK_KEYWORDS.items():
                if any(keyword.lower() in full_text for keyword in keywords):
                    tags.add(tag)
            if item.estimated_drive_hours >= 5 or item.distance_km >= 300:
                tags.add("long_transfer")
        return tags

    def validate_rush_day(self, checklist: dict[str, bool], tags: set[str]) -> RushDayValidation:
        is_rush_day = "long_transfer" in tags or "early_checkout" in tags
        if not is_rush_day:
            return RushDayValidation(is_rush_day=False, passed=True)

        missing_items = [
            label
            for key, label in self.RUSH_DAY_REQUIRED_KEYS.items()
            if not checklist.get(key, False)
        ]
        return RushDayValidation(
            is_rush_day=True,
            passed=not missing_items,
            missing_items=missing_items,
        )

    def build_report(
        self,
        items: Iterable[ItineraryItem],
        checklist: dict[str, bool],
    ) -> ItineraryRiskReport:
        tags = self.detect_risk_tags(items)
        return ItineraryRiskReport(
            risk_tags=tags,
            rush_day_validation=self.validate_rush_day(checklist, tags),
        )
