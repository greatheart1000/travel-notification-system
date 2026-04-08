from __future__ import annotations

import pytest

from app.modules.notification.concierge_playbook import (
    WORKFLOW_STEPS,
    MESSAGE_TEMPLATES,
    get_template,
)


def test_workflow_steps_cover_key_stages() -> None:
    stage_names = {step.stage for step in WORKFLOW_STEPS}

    assert "T-3天出发确认" in stage_names
    assert "在途日常运营" in stage_names
    assert "下团售后" in stage_names


def test_get_template_returns_expected_message() -> None:
    message = get_template("group_welcome")

    assert "欢迎来到美丽的新疆" in message
    assert "AI小管家小琪" in message


def test_get_template_raises_when_key_missing() -> None:
    with pytest.raises(KeyError):
        get_template("unknown_template")


def test_template_catalog_contains_operational_scenes() -> None:
    assert "pre_flight_notice" in MESSAGE_TEMPLATES
    assert "horse_riding_notice" in MESSAGE_TEMPLATES
    assert "group_close_message" in MESSAGE_TEMPLATES
