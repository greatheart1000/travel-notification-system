from __future__ import annotations

from app.core.models import Channel, NotificationType
from app.services.lifecycle_rule_builder import JourneyStage, LifecycleRuleBuilder


def test_builder_generates_full_lifecycle_drafts() -> None:
    builder = LifecycleRuleBuilder()

    drafts = builder.build_default_drafts()

    assert len(drafts) == 10
    assert {draft.stage for draft in drafts} == {
        JourneyStage.PRE_TRIP,
        JourneyStage.ON_TRIP,
        JourneyStage.POST_TRIP,
    }
    assert drafts[0].time_node == "出发前3天"
    assert drafts[-1].notification_type == NotificationType.FAREWELL


def test_builder_converts_drafts_to_trigger_rules_and_templates() -> None:
    builder = LifecycleRuleBuilder()
    drafts = builder.build_default_drafts()

    rules = builder.to_trigger_rules(drafts)
    templates = builder.to_notification_templates(drafts, channel=Channel.SMS)

    assert len(rules) == len(drafts)
    assert len(templates) == len(drafts)
    assert rules[4].conditions == {
        "time_window": {"op": "in", "value": ["morning", "noon", "evening"]}
    }
    assert templates[0].name == "pre_t_minus_3_customer_check_v1"
    assert templates[0].channel == Channel.SMS
    assert "游客沟通+行程单处理" in templates[0].content
