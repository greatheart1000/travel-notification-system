from __future__ import annotations

from datetime import date, timedelta

from app.core.models import Channel
from app.modules.notification.models import NotificationTemplate
from app.modules.notification.service import NotificationService
from app.services.template_service import TemplateService
from app.services.workflow_orchestrator import WorkflowOrchestrator
from tests.fakes import FakeChannelProvider, fake_providers


class _TripRepo:
    def __init__(self, trips):
        self._trips = trips

    def list(self):
        return list(self._trips)


def _template_service() -> TemplateService:
    service = TemplateService()
    templates = {
        "tpl-pre-3d": "T-3 {{customer_name}} {{destination}}",
        "tpl-pre-1d-welcome": "T-1 welcome {{customer_name}}",
        "tpl-pre-1d-tips": "T-1 tips {{customer_name}}",
        "tpl-arrival-urumqi": "arrival {{customer_name}}",
        "tpl-post-farewell": "farewell {{customer_name}}",
        "tpl-morning-spring": "morning spring {{customer_name}}",
        "tpl-morning-summer": "morning summer {{customer_name}}",
        "tpl-morning-autumn": "morning autumn {{customer_name}}",
        "tpl-morning-winter": "morning winter {{customer_name}}",
    }
    for template_id, content in templates.items():
        service.notification_templates[template_id] = NotificationTemplate(
            id=template_id,
            tenant_id="tenant-a",
            name=template_id,
            content=content,
            channel=Channel.SMS,
            is_active=True,
        )
    return service


def _build(trips):
    sms = FakeChannelProvider(default=(True, "ok"))
    service = NotificationService(providers=fake_providers(sms=sms))
    orchestrator = WorkflowOrchestrator(
        trip_repository=_TripRepo(trips),
        template_service=_template_service(),
        notification_service=service,
    )
    return orchestrator, sms


def _trip(start_offset: int, end_offset: int, **overrides):
    today = date.today()
    trip = {
        "id": f"trip-{start_offset}-{end_offset}",
        "tenant_id": "tenant-a",
        "team_id": "TEAM-1",
        "destination": "阿勒泰",
        "status": "planned",
        "start_date": (today + timedelta(days=start_offset)).isoformat(),
        "end_date": (today + timedelta(days=end_offset)).isoformat(),
        "guests": [{"name": "张三"}],
        "itinerary": [],
    }
    trip.update(overrides)
    return trip


def test_scan_sends_t3_reminder() -> None:
    orchestrator, sms = _build([_trip(3, 5)])

    result = orchestrator.scan_and_trigger(tenant_id="tenant-a")

    assert result["triggered_total"] == 1
    assert sms.call_count == 1


def test_scan_sends_t1_bundle() -> None:
    orchestrator, sms = _build([_trip(1, 4)])

    result = orchestrator.scan_and_trigger(tenant_id="tenant-a")

    assert result["triggered_total"] == 2
    assert sms.call_count == 2


def test_scan_sends_daily_morning_while_in_progress() -> None:
    orchestrator, sms = _build([_trip(-1, 2, status="in_progress")])

    result = orchestrator.scan_and_trigger(tenant_id="tenant-a")

    assert result["triggered_total"] == 1
    assert sms.call_count == 1


def test_scan_sends_farewell_on_end_day() -> None:
    orchestrator, sms = _build([_trip(-2, 0, status="completed")])

    result = orchestrator.scan_and_trigger(tenant_id="tenant-a")

    assert result["triggered_total"] == 1
    assert sms.call_count == 1
    assert "farewell" in sms.calls[0]["content"]
