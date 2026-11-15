from __future__ import annotations

import pytest

from app.modules.notification.rule_service import (
    NotificationRuleRepository,
    RuleValidationError,
    normalize_channels,
    normalize_stage,
)


def _repo(json_store) -> NotificationRuleRepository:
    return NotificationRuleRepository(store=json_store)


def test_normalize_stage_and_channels_support_chinese_aliases() -> None:
    assert normalize_stage("行前") == "pre_trip"
    assert normalize_stage("before_departure") == "pre_trip"
    assert normalize_channels(["短信", "sms", "企业微信"]) == ["sms", "wechat_work_group"]


def test_rule_simulation_matches_conditions_and_tenant(json_store) -> None:
    repo = _repo(json_store)
    repo.create_rule(
        {
            "tenant_id": "tenant-a",
            "name": "新疆行前提醒",
            "stage": "行前",
            "time_slot": "morning",
            "scene": "normal",
            "channels": ["短信"],
            "conditions": {"destination": "新疆"},
            "priority": 10,
        }
    )

    matched = repo.simulate(
        tenant_id="tenant-a",
        stage="pre_trip",
        time_slot="morning",
        scene="normal",
        context={"destination": "新疆"},
    )
    mismatch = repo.simulate(
        tenant_id="tenant-a",
        stage="pre_trip",
        time_slot="morning",
        scene="normal",
        context={"destination": "海南"},
    )
    other_tenant = repo.simulate(
        tenant_id="tenant-b",
        stage="pre_trip",
        time_slot="morning",
        scene="normal",
        context={"destination": "新疆"},
    )

    assert [item["name"] for item in matched["matches"]] == ["新疆行前提醒"]
    assert matched["conflicts"] == []
    assert mismatch["matches"] == []
    assert other_tenant["matches"] == []


def test_rule_priority_conflict_is_reported(json_store) -> None:
    repo = _repo(json_store)
    for name in ("rule-1", "rule-2"):
        repo.create_rule(
            {
                "tenant_id": "tenant-a",
                "name": name,
                "stage": "in_trip",
                "time_slot": "morning",
                "scene": "normal",
                "channels": ["sms"],
                "priority": 10,
            }
        )

    result = repo.simulate(
        tenant_id="tenant-a",
        stage="in_trip",
        time_slot="morning",
        scene="normal",
    )

    assert len(result["matches"]) == 2
    assert result["conflicts"] == ["multiple_rules_share_top_priority"]


def test_rule_status_transition_and_invalid_transition(json_store) -> None:
    repo = _repo(json_store)
    rule = repo.create_rule(
        {
            "tenant_id": "tenant-a",
            "name": "approval",
            "stage": "post_trip",
            "time_slot": "evening",
            "scene": "normal",
            "channels": ["sms"],
            "status": "draft",
        }
    )

    submitted = repo.submit_rule(rule["id"], tenant_id="tenant-a", operator_id="ops-1")
    approved = repo.approve_rule(rule["id"], tenant_id="tenant-a", operator_id="mgr-1")
    published = repo.publish_rule(rule["id"], tenant_id="tenant-a", operator_id="mgr-1")

    assert submitted is not None and submitted["status"] == "pending_approval"
    assert approved is not None and approved["status"] == "approved"
    assert published is not None and published["status"] == "published"
    assert published["enabled"] is True

    with pytest.raises(RuleValidationError):
        repo.approve_rule(rule["id"], tenant_id="tenant-a", operator_id="mgr-1")


def test_rule_list_filters_tenant_and_scene(json_store) -> None:
    repo = _repo(json_store)
    repo.create_rule(
        {
            "tenant_id": "tenant-a",
            "name": "weather",
            "stage": "in_trip",
            "time_slot": "all_day",
            "scene": "weather",
            "channels": ["wechat_work_group"],
        }
    )
    repo.create_rule(
        {
            "tenant_id": "tenant-b",
            "name": "other",
            "stage": "in_trip",
            "time_slot": "all_day",
            "scene": "weather",
            "channels": ["sms"],
        }
    )

    items = repo.list_rules(tenant_id="tenant-a", scene="weather_alert")

    assert [item["name"] for item in items] == ["weather"]
