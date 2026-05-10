from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.modules.integration.weather_provider import WeatherInfo
from app.modules.notification.service import NotificationService
from app.services.risk_notification_service import RiskEvidenceRepository, RiskNotificationWorkflow
from app.services.template_service import TemplateService


class _TripRepo:
    def __init__(self, trips: list[dict[str, Any]]) -> None:
        self._trips = trips

    def list(self) -> list[dict[str, Any]]:
        return list(self._trips)


class _WeatherProvider:
    def get_weather(
        self,
        destination: str,
        location_context: dict[str, Any] | None = None,
    ) -> WeatherInfo:
        return WeatherInfo(
            destination=destination,
            condition="小雪",
            temperature=-18.0,
            warning_level="orange",
            alert_title="道路结冰橙色预警",
            hourly_forecast=[
                {"fxTime": "2026-05-11T09:00+08:00", "text": "小雪", "temp": "-18", "windScale": "3"},
                {"fxTime": "2026-05-11T12:00+08:00", "text": "大风", "temp": "-12", "windScale": "7"},
            ],
            source="qweather",
        )


class _Audit:
    def __init__(self) -> None:
        self.logs: list[dict[str, Any]] = []

    def record(self, operator_id: str, action: str, target: str, detail: dict[str, Any]) -> None:
        self.logs.append(
            {"operator_id": operator_id, "action": action, "target": target, "detail": detail}
        )


def _build_workflow(trips: list[dict[str, Any]]) -> tuple[RiskNotificationWorkflow, _Audit]:
    template_service = TemplateService()
    template_service.create_notification_template(
        tenant_id="tenant-a",
        project_id="proj-xj",
        name="特殊风险企微模板",
        content="【{{ alert_title }}】{{ risk_tags }} {{ itinerary_title }} {{ weather_text }} {{ recommendation_actions }}",
        channel="wechat_work_group",
        notification_type="risk_alert",
        is_active=True,
        stage="in_trip",
        time_slot="all_day",
        scene="manual",
    )
    template_service.create_notification_template(
        tenant_id="tenant-a",
        project_id="proj-xj",
        name="天气风险企微模板",
        content="【{{ alert_title }}】{{ weather_text }} {{ recommendation_actions }}",
        channel="wechat_work_group",
        notification_type="risk_alert",
        is_active=True,
        stage="in_trip",
        time_slot="all_day",
        scene="weather_alert",
    )
    audit = _Audit()
    workflow = RiskNotificationWorkflow(
        trip_repository=_TripRepo(trips),
        template_service=template_service,
        notification_service=NotificationService(),
        weather_provider=_WeatherProvider(),  # type: ignore[arg-type]
        evidence_repository=RiskEvidenceRepository(),
        audit_service=audit,
    )
    return workflow, audit


def test_sync_erp_risk_tags_normalizes_trip_and_itinerary_tags() -> None:
    workflow, _ = _build_workflow([])
    synced = workflow.sync_erp_risk_tags(
        {
            "id": "trip-1",
            "tenant_id": "tenant-a",
            "business_tags": ["高原", "边境"],
            "itinerary": [
                {
                    "date": "2026-05-11",
                    "title": "喀纳斯骑马体验",
                    "description": "雪场装备检查后进入无人区边缘观景",
                }
            ],
        }
    )

    assert set(synced["risk_tags"]) >= {"highland", "border", "horse_riding", "skiing", "no_man_land"}
    assert set(synced["itinerary"][0]["risk_tags"]) >= {"horse_riding", "skiing", "no_man_land"}
    assert synced["erp_risk_tag_synced_at"]


def test_build_triggers_covers_previous_day_current_day_weather_24h_and_transport_change() -> None:
    workflow, _ = _build_workflow(
        [
            {
                "id": "trip-1",
                "tenant_id": "tenant-a",
                "team_id": "TEAM-1",
                "project_id": "proj-xj",
                "destination": "阿勒泰",
                "status": "in_progress",
                "start_date": "2026-05-10",
                "itinerary": [
                    {"date": "2026-05-10", "title": "高原口岸", "description": "边境口岸检查"},
                    {"date": "2026-05-11", "title": "骑马滑雪", "description": "骑马后前往雪场"},
                ],
                "flight_updates": [{"type": "航班", "code": "CZ1234", "status": "delayed"}],
            }
        ]
    )

    triggers = workflow.build_triggers(
        tenant_id="tenant-a",
        now=datetime(2026, 5, 10, 8, 0, tzinfo=UTC),
    )

    trigger_types = {trigger.risk_type for trigger in triggers}
    timings = {trigger.trigger_timing for trigger in triggers}
    assert {"special_scene", "weather_24h", "transport_change"} <= trigger_types
    assert {"current_day", "previous_day", "within_24h", "realtime_change"} <= timings
    weather_trigger = next(trigger for trigger in triggers if trigger.risk_type == "weather_24h")
    assert "qweather_24h_extreme_cold" in weather_trigger.hit_rules
    assert "qweather_24h_strong_wind" in weather_trigger.hit_rules


def test_send_due_risks_keeps_wecom_evidence_and_supports_confirmation_and_escalation() -> None:
    workflow, audit = _build_workflow(
        [
            {
                "id": "trip-1",
                "tenant_id": "tenant-a",
                "team_id": "TEAM-1",
                "project_id": "proj-xj",
                "destination": "阿勒泰",
                "status": "in_progress",
                "start_date": "2026-05-10",
                "itinerary": [
                    {"date": "2026-05-11", "title": "骑马滑雪", "description": "骑马后前往雪场"},
                ],
            }
        ]
    )
    now = datetime(2026, 5, 10, 8, 0, tzinfo=UTC)

    result = workflow.send_due_risks(tenant_id="tenant-a", now=now)

    assert result["sent_count"] >= 2
    evidence_items = workflow.evidence_repository.list(tenant_id="tenant-a")
    assert all(item["channel"] == "wechat_work_group" for item in evidence_items)
    assert all(item["receipt_status"] == "provider_accepted" for item in evidence_items)
    assert all(item["concierge_confirmation_status"] == "pending" for item in evidence_items)
    assert any("骑马" in item["content"] or "滑雪" in item["content"] for item in evidence_items)

    confirmed = workflow.confirm(evidence_items[0]["evidence_id"], operator_id="concierge-1", now=now)
    assert confirmed["concierge_confirmation_status"] == "confirmed"
    assert confirmed["concierge_confirmed_by"] == "concierge-1"

    escalated = workflow.escalate_overdue(
        tenant_id="tenant-a",
        now=now + timedelta(minutes=16),
        timeout_minutes=15,
    )
    assert escalated
    assert all(item["escalated"] for item in escalated)
    assert "risk_notification_sent" in {item["action"] for item in audit.logs}
    assert "risk_notification_escalated" in {item["action"] for item in audit.logs}
