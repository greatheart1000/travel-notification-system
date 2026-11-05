from __future__ import annotations

from app.modules.notification.policy import NotificationPolicy
from app.modules.notification.rule_service import NotificationRuleRepository


def _repo(json_store) -> NotificationRuleRepository:
    return NotificationRuleRepository(store=json_store)


def _create_rule(repo: NotificationRuleRepository, **overrides):
    payload = {
        "tenant_id": "tenant-a",
        "name": "行前晨间规则",
        "stage": "pre_trip",
        "time_slot": "morning",
        "scene": "normal",
        "channels": ["sms"],
        "conditions": {"destination": "阿勒泰"},
        "enabled": True,
    }
    payload.update(overrides)
    return repo.create_rule(payload)


def test_policy_without_rules_allows_legacy_behavior(json_store) -> None:
    policy = NotificationPolicy(_repo(json_store))

    decision = policy.resolve(
        tenant_id="tenant-a",
        stage="pre_trip",
        time_slot="morning",
        scene="normal",
        context={"destination": "阿勒泰"},
    )

    assert decision.configured is False
    assert decision.allowed is True


def test_policy_allows_matching_rule(json_store) -> None:
    repo = _repo(json_store)
    _create_rule(repo)
    policy = NotificationPolicy(repo)

    decision = policy.resolve(
        tenant_id="tenant-a",
        stage="pre_trip",
        time_slot="morning",
        scene="normal",
        context={"destination": "阿勒泰"},
    )

    assert decision.configured is True
    assert decision.allowed is True
    assert decision.channels == ["sms"]
    assert decision.rule_ids


def test_policy_blocks_when_conditions_do_not_match(json_store) -> None:
    repo = _repo(json_store)
    _create_rule(repo)
    policy = NotificationPolicy(repo)

    decision = policy.resolve(
        tenant_id="tenant-a",
        stage="pre_trip",
        time_slot="morning",
        scene="normal",
        context={"destination": "海南"},
    )

    assert decision.configured is True
    assert decision.allowed is False


def test_policy_treats_all_day_as_wildcard(json_store) -> None:
    repo = _repo(json_store)
    _create_rule(repo, time_slot="all_day", conditions={})
    policy = NotificationPolicy(repo)

    decision = policy.resolve(
        tenant_id="tenant-a",
        stage="pre_trip",
        time_slot="afternoon",
        scene="normal",
        context={},
    )

    assert decision.allowed is True


def test_policy_isolates_tenants(json_store) -> None:
    repo = _repo(json_store)
    _create_rule(repo, tenant_id="tenant-a", conditions={})
    policy = NotificationPolicy(repo)

    decision = policy.resolve(
        tenant_id="tenant-b",
        stage="pre_trip",
        time_slot="morning",
        scene="normal",
        context={},
    )

    assert decision.configured is False
    assert decision.allowed is True
