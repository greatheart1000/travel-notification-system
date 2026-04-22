from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _safe_text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def _stage_impact(status: str) -> str:
    mapping = {
        "planned": "出发",
        "in_progress": "途中/景点",
        "completed": "返程",
        "cancelled": "出发",
    }
    return mapping.get(status, "途中/景点")


@dataclass(slots=True)
class WeatherAlertAIService:
    """Minimal deterministic copy generator for weather emergency notification."""

    def generate(
        self,
        *,
        weather_summary: str,
        risk_level_label: str,
        affected_region: str,
        affected_trips: list[dict[str, Any]],
        recommendation_actions: list[str],
    ) -> dict[str, Any]:
        trip_count = len(affected_trips)
        trip_names = [
            _safe_text(item.get("destination")) or _safe_text(item.get("team_id"), "未命名团")
            for item in affected_trips[:3]
        ]
        stages = sorted({_stage_impact(_safe_text(item.get("status"))) for item in affected_trips})
        stage_text = "、".join(stages) if stages else "出发"
        recommend_send = risk_level_label in {"较高", "高危"}

        action_text = recommendation_actions[:3]
        if not action_text:
            action_text = ["建议领队提前通报集合点调整", "建议游客减少户外停留时间"]

        tourist_copy = (
            f"【天气提醒】{affected_region}今日天气变化明显。{weather_summary}。"
            f"AI评估风险等级：{risk_level_label}，预计影响{trip_count}个旅行团（{ '、'.join(trip_names) or '相关团队' }）。"
            "请携带雨具和保暖衣物，关注领队发布的集合时间与路线调整通知。"
        )
        internal_copy = (
            f"【内部预警】区域：{affected_region}；风险等级：{risk_level_label}；"
            f"受影响环节：{stage_text}；受影响团数：{trip_count}。"
            f"建议动作：{'；'.join(action_text)}。"
            "建议人工确认后分批发送游客通知，并同步领队群执行调整。"
        )

        return {
            "ai_risk_analysis": {
                "affected_trip_ids": [_safe_text(item.get("trip_id")) for item in affected_trips],
                "affected_stage": stage_text,
                "recommend_send": recommend_send,
                "summary": (
                    f"AI识别{trip_count}个旅行团受影响，主要影响环节为{stage_text}，"
                    f"建议动作：{'；'.join(action_text)}。"
                ),
            },
            "generated_copies": {
                "tourist": tourist_copy,
                "internal": internal_copy,
            },
            "suggested_actions": action_text,
        }
