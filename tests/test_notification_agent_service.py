from __future__ import annotations

from app.services.notification_agent_service import (
    AlgorithmAgent,
    NotificationAgentService,
    ValidatorAgent,
)


def test_algorithm_agent_resolves_stage() -> None:
    agent = AlgorithmAgent()

    assert agent.resolve_stage(
        travel_date="2026-05-01", start_date="2026-05-03", end_date="2026-05-06"
    ) == "行程前"
    assert agent.resolve_stage(
        travel_date="2026-05-03", start_date="2026-05-03", end_date="2026-05-06"
    ) == "行程中"
    assert agent.resolve_stage(
        travel_date="2026-05-06", start_date="2026-05-03", end_date="2026-05-06"
    ) == "下团即付"
    assert agent.resolve_stage(
        travel_date="2026-05-07", start_date="2026-05-03", end_date="2026-05-06"
    ) == "下团后短期"
    assert agent.resolve_stage(
        travel_date="bad", start_date="also-bad", end_date="bad"
    ) == "行程中"


def test_validator_appends_missing_priority_points() -> None:
    validator = ValidatorAgent()

    message, missing = validator.validate(
        message="今日路线：阿勒泰",
        priority_points=["集合时间", "安全带"],
    )

    assert missing == ["集合时间", "安全带"]
    assert "请关注" in message


def test_generate_daily_messages_falls_back_without_llm(monkeypatch) -> None:
    monkeypatch.delenv("GLM_API_KEY", raising=False)
    service = NotificationAgentService()

    result = service.generate_daily_messages(
        group_id="TEAM-1",
        group_name="阿勒泰团",
        travel_date="2026-05-04",
        start_date="2026-05-03",
        end_date="2026-05-06",
        route_text="喀纳斯",
        hotel="木屋酒店",
        weather="晴",
        core_work="每日提示",
        special_tags=["骑马"],
    )

    assert result["stage"] == "行程中"
    assert len(result["messages"]) == 3
    assert {item["period"] for item in result["messages"]} == {"morning", "noon", "evening"}
    assert all(item["message"] for item in result["messages"])


def test_generate_daily_drafts_returns_three_periods() -> None:
    service = NotificationAgentService()

    result = service.generate_daily_drafts(
        route="喀纳斯",
        travel_stage="行程中",
        time_node="每日固定时段",
        core_work="每日提示",
        action_detail="确认车辆",
    )

    assert len(result["drafts"]) == 3
    assert "确认车辆" in result["context"]["prompt_summary"]
