from __future__ import annotations

from datetime import datetime, timedelta

from app.core.models import UTC
from app.modules.audit.service import AuditLogRepository, AuditService
from app.modules.integration.persistence import JsonFileStore
from app.modules.trigger.engine import TriggerEngine
from app.modules.trigger.models import TriggerRule


def test_trigger_engine_supports_operator_conditions() -> None:
    engine = TriggerEngine()
    rule = TriggerRule(
        code="weather-cold",
        name="极寒提醒",
        conditions={
            "temperature": {"op": "<=", "value": -10},
            "uv": {"op": "in", "value": ["high", "extreme"]},
        },
    )

    assert engine.evaluate(rule, {"temperature": -12, "uv": "high"}) is True
    assert engine.evaluate(rule, {"temperature": -5, "uv": "high"}) is False


def test_trigger_engine_honors_enabled_and_effective_window() -> None:
    engine = TriggerEngine()
    now = datetime.now(tz=UTC)
    rule = TriggerRule(
        code="weather-window",
        name="时效天气提醒",
        enabled=True,
        effective_from=now - timedelta(minutes=5),
        effective_to=now + timedelta(minutes=5),
        conditions={"risk_level": {"op": "in", "value": ["high", "critical"]}},
    )
    assert engine.evaluate(rule, {"risk_level": "high"}, now=now) is True

    disabled = TriggerRule(code="disabled", name="停用规则", enabled=False, is_mandatory=True)
    assert engine.evaluate(disabled, {}, now=now) is False

    expired = TriggerRule(
        code="expired",
        name="过期规则",
        enabled=True,
        effective_to=now - timedelta(minutes=1),
        is_mandatory=True,
    )
    assert engine.evaluate(expired, {}, now=now) is False


def test_audit_service_records_and_queries() -> None:
    audit = AuditService()
    audit.record(
        operator_id="admin-1", action="dispatch", target="TEAM-001", detail={"channel": "sms"}
    )
    audit.record(
        operator_id="admin-2", action="template_update", target="TEAM-002", detail={"version": 2}
    )

    team_logs = audit.repository.list_by_target("TEAM-001")

    assert len(team_logs) == 1
    assert team_logs[0].action == "dispatch"


def test_audit_service_persists_logs(tmp_path) -> None:
    store = JsonFileStore(base_dir=tmp_path)
    repository = AuditLogRepository(store=store)
    audit = AuditService(repository=repository)

    audit.record(
        operator_id="admin-1", action="trip_created", target="trip-001", detail={"team": "TEAM-001"}
    )

    reloaded = AuditLogRepository(store=store)
    logs = reloaded.list_by_target("trip-001")
    assert len(logs) == 1
    assert logs[0].action == "trip_created"
