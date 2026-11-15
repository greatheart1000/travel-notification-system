from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.modules.billing.models import Subscription
from app.modules.billing.service import BillingService
from app.modules.identity.models import Tenant
from app.modules.identity.repository import TenantRepository
from app.modules.integration.persistence import JsonFileStore
from app.services.billing_dunning_service import BillingDunningService


class _EmailRecorder:
    def __init__(self, *, ok: bool = True) -> None:
        self.ok = ok
        self.sent: list[dict[str, str]] = []

    def send(self, to: str, subject: str, body: str) -> bool:
        if not self.ok:
            return False
        self.sent.append({"to": to, "subject": subject, "body": body})
        return True


def _setup(tmp_path, *, now: datetime):
    store = JsonFileStore(base_dir=tmp_path)
    billing = BillingService(store, providers={}, clock=lambda: now)
    tenants = TenantRepository(store)
    tenants.create(
        Tenant(
            id="tenant-a",
            name="测试旅行社",
            contact_email="billing@example.com",
        )
    )
    return store, billing, tenants


def test_dunning_sends_paid_plan_reminder_once(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("BILLING_DUNNING_ENABLED", "true")
    now = datetime(2026, 1, 1, tzinfo=UTC)
    store, billing, tenants = _setup(tmp_path, now=now)
    billing.activate_plan("tenant-a", "starter", days=7)
    email = _EmailRecorder()
    service = BillingDunningService(
        billing_service=billing,
        tenant_repository=tenants,
        store=store,
        email_provider=email,
        base_url="https://travel.example.com",
    )

    first = service.run(now=now)
    second = service.run(now=now)

    assert first["sent"] == 1
    assert second["sent"] == 0
    assert second["skipped"] == 1
    assert email.sent[0]["to"] == "billing@example.com"
    assert "套餐即将到期" in email.sent[0]["subject"]
    assert "剩余 7 天" in email.sent[0]["body"]
    assert "https://travel.example.com/billing" in email.sent[0]["body"]


def test_dunning_reminds_trial_expiry(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("BILLING_DUNNING_ENABLED", "true")
    now = datetime(2026, 1, 1, tzinfo=UTC)
    store, billing, tenants = _setup(tmp_path, now=now)
    billing.subscriptions.upsert(
        Subscription(
            tenant_id="tenant-a",
            plan_code="trial",
            status="trialing",
            started_at=now.isoformat(),
            current_period_start=now.isoformat(),
            current_period_end=(now + timedelta(days=3)).isoformat(),
        )
    )
    email = _EmailRecorder()
    service = BillingDunningService(
        billing_service=billing,
        tenant_repository=tenants,
        store=store,
        email_provider=email,
    )

    summary = service.run(now=now)

    assert summary["sent"] == 1
    assert "试用即将到期" in email.sent[0]["subject"]
    assert "剩余 3 天" in email.sent[0]["body"]


def test_dunning_skips_when_email_provider_missing(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("BILLING_DUNNING_ENABLED", "true")
    now = datetime(2026, 1, 1, tzinfo=UTC)
    store, billing, tenants = _setup(tmp_path, now=now)
    billing.activate_plan("tenant-a", "starter", days=7)
    service = BillingDunningService(
        billing_service=billing,
        tenant_repository=tenants,
        store=store,
        email_provider=None,
    )

    summary = service.run(now=now)

    assert summary["sent"] == 0
    assert summary["reason"] == "email_provider_not_configured"


def test_dunning_can_be_disabled(monkeypatch, tmp_path) -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    store, billing, tenants = _setup(tmp_path, now=now)
    billing.activate_plan("tenant-a", "starter", days=7)
    email = _EmailRecorder()
    service = BillingDunningService(
        billing_service=billing,
        tenant_repository=tenants,
        store=store,
        email_provider=email,
    )
    monkeypatch.setenv("BILLING_DUNNING_ENABLED", "false")

    summary = service.run(now=now)

    assert summary["enabled"] is False
    assert summary["sent"] == 0
    assert email.sent == []
