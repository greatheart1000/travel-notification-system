from __future__ import annotations

from datetime import timedelta

import pytest

from app.modules.notification.checklist_service import ChecklistService
from app.modules.notification.models import NotificationTemplate
from app.modules.notification.service import NotificationService
from app.modules.trigger.itinerary_service import ItineraryItem, ItineraryRiskService
from app.modules.trigger.risk_alert_service import RiskAlertService, RiskResponseLevel, RiskSignal


def test_itinerary_risk_service_detects_tags_and_rush_day_validation() -> None:
    service = ItineraryRiskService()
    report = service.build_report(
        items=[
            ItineraryItem(
                day="D2",
                title="禾木-喀纳斯长途转场",
                description="早起退房后车程 360 公里，下午安排骑马体验",
                distance_km=360,
                estimated_drive_hours=6.5,
            )
        ],
        checklist={
            "breakfast_packed": True,
            "meeting_time_confirmed": False,
            "vehicle_buffer_checked": True,
            "critical_resource_ready": False,
        },
    )

    assert "horse_riding" in report.risk_tags
    assert "long_transfer" in report.risk_tags
    assert report.rush_day_validation.is_rush_day is True
    assert report.rush_day_validation.passed is False
    assert report.rush_day_validation.missing_items == ["集合时间确认", "关键资源准备"]


def test_risk_alert_service_supports_three_level_response() -> None:
    service = RiskAlertService()

    auto = service.evaluate(
        RiskSignal(weather="rain", road_status="normal", temperature=5, wind_scale=3, unresolved_minutes=0)
    )
    assert auto is not None
    assert auto.response_level == RiskResponseLevel.AUTO_SENT

    manager_confirm = service.evaluate(
        RiskSignal(
            weather="snow",
            road_status="congested",
            temperature=-18,
            wind_scale=7,
            unresolved_minutes=7,
        )
    )
    assert manager_confirm is not None
    assert manager_confirm.response_level == RiskResponseLevel.MANAGER_CONFIRMED

    escalated = service.evaluate(
        RiskSignal(
            weather="snow",
            road_status="closed",
            temperature=-20,
            wind_scale=8,
            unresolved_minutes=20,
        )
    )
    assert escalated is not None
    assert escalated.response_level == RiskResponseLevel.MANAGEMENT_ESCALATED


def test_checklist_service_requires_mandatory_confirmation_and_escalates() -> None:
    service = ChecklistService()
    checklist = service.build_for_risk_tags("trip-1", {"horse_riding", "highland"})

    assert any(task.code == "horse_riding_safety" and task.mandatory for task in checklist.tasks)
    assert any(task.code == "highland_health_tip" and task.mandatory for task in checklist.tasks)

    now = checklist.generated_at + timedelta(minutes=31)
    assert service.needs_escalation(checklist, now=now, timeout_minutes=30) is True

    service.confirm_task(checklist, "horse_riding_safety")
    service.confirm_task(checklist, "highland_health_tip")
    assert service.needs_escalation(checklist, now=now, timeout_minutes=30) is False


def test_notification_template_render_raises_when_variables_missing() -> None:
    service = NotificationService()
    template = NotificationTemplate(content="{{customer_name}}您好，目的地{{destination}}")

    with pytest.raises(ValueError, match="missing_template_variables:destination"):
        service.render(template, {"customer_name": "张三"})

    rendered = service.render(template, {"customer_name": "张三", "destination": "阿勒泰"})
    assert rendered == "张三您好，目的地阿勒泰"
