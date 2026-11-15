from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.modules.trigger.engine import TriggerEngine
from app.modules.trigger.models import TriggerRule
from app.modules.trigger.risk_alert_service import RiskAlertService, RiskSignal


def _rule(conditions: dict, **overrides) -> TriggerRule:
    payload = {
        "code": "rule-1",
        "name": "rule",
        "conditions": conditions,
        "priority": 10,
        "enabled": True,
    }
    payload.update(overrides)
    return TriggerRule(**payload)


def test_trigger_engine_supports_comparison_and_membership_operators() -> None:
    engine = TriggerEngine()
    now = datetime(2026, 5, 10, tzinfo=UTC)
    context = {"temperature": -18, "weather": "snow", "tags": ["高原", "骑马"], "wind": 7}

    assert engine.evaluate(_rule({"temperature": {"op": "<=", "value": -15}}), context, now=now)
    assert engine.evaluate(_rule({"weather": {"op": "in", "value": ["snow", "rain"]}}), context, now=now)
    assert engine.evaluate(_rule({"tags": {"op": "contains", "value": "骑马"}}), context, now=now)
    assert engine.evaluate(_rule({"tags": ["极寒", "骑马"]}), context, now=now)
    assert not engine.evaluate(_rule({"tags": ["滑雪"]}), context, now=now)
    assert not engine.evaluate(_rule({"wind": {"op": ">", "value": 8}}), context, now=now)
    assert not engine.evaluate(_rule({"missing": "x"}), context, now=now)


def test_mandatory_rule_matches_even_without_conditions_but_disabled_does_not() -> None:
    engine = TriggerEngine()
    now = datetime(2026, 5, 10, tzinfo=UTC)

    assert engine.evaluate(_rule({}, is_mandatory=True), {}, now=now)
    assert not engine.evaluate(_rule({}, is_mandatory=True, enabled=False), {}, now=now)


def test_rule_effective_window_is_respected() -> None:
    engine = TriggerEngine()
    now = datetime(2026, 5, 10, tzinfo=UTC)
    rule = _rule(
        {},
        is_mandatory=True,
        effective_from=now - timedelta(days=1),
        effective_to=now + timedelta(days=1),
    )
    expired = _rule(
        {},
        is_mandatory=True,
        effective_to=now - timedelta(seconds=1),
    )

    assert engine.evaluate(rule, {}, now=now)
    assert not engine.evaluate(expired, {}, now=now)


def test_pick_first_matched_uses_priority() -> None:
    engine = TriggerEngine()
    low = _rule({}, is_mandatory=True, priority=100, code="low")
    high = _rule({}, is_mandatory=True, priority=1, code="high")

    picked = engine.pick_first_matched([low, high], {})

    assert picked is not None
    assert picked.code == "high"


def test_risk_alert_service_escalates_based_on_unresolved_minutes() -> None:
    service = RiskAlertService()

    auto = service.evaluate(
        RiskSignal(weather="snow", road_status="normal", temperature=-10, wind_scale=3)
    )
    manager = service.evaluate(
        RiskSignal(
            weather="snow",
            road_status="normal",
            temperature=-10,
            wind_scale=3,
            unresolved_minutes=5,
        )
    )
    escalated = service.evaluate(
        RiskSignal(
            weather="snow",
            road_status="closed",
            temperature=-20,
            wind_scale=8,
            unresolved_minutes=15,
        )
    )

    assert auto is not None and auto.level == "high"
    assert manager is not None and manager.response_level.value == "manager_confirmed"
    assert escalated is not None
    assert escalated.level == "critical"
    assert escalated.response_level.value == "management_escalated"
    assert service.evaluate(
        RiskSignal(weather="clear", road_status="normal", temperature=20, wind_scale=2)
    ) is None
