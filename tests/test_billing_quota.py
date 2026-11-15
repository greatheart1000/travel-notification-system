from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.core.models import Channel
from app.modules.billing.service import BillingService
from app.modules.integration.persistence import JsonFileStore
from app.modules.notification.provider_registry import (
    QuotaEnforcingSMSProvider,
    TenantNotificationConfigRepository,
    TenantProviderRegistry,
)


class CountingProvider:
    def __init__(self) -> None:
        self.calls = 0

    def send(self, customer_id, content, provider_context=None):
        self.calls += 1
        return True, f"ok:{customer_id}"


def test_quota_enforcing_provider_blocks_after_quota(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("BILLING_TRIAL_SMS_QUOTA", "2")
    monkeypatch.setenv("BILLING_TRIAL_DAYS", "14")
    store = JsonFileStore(base_dir=tmp_path)
    billing = BillingService(store=store, providers={})
    inner = CountingProvider()
    provider = QuotaEnforcingSMSProvider(
        tenant_id="tenant-quota",
        billing_service=billing,
        inner=inner,
    )
    assert provider.send("13800000001", "hello") == (True, "ok:13800000001")
    assert provider.send("13800000001", "hello") == (True, "ok:13800000001")
    ok, reason = provider.send("13800000001", "hello")
    assert ok is False
    assert reason == "sms_quota_exceeded"
    assert inner.calls == 2
    assert billing.usage_view("tenant-quota").sms_used == 2


def test_provider_registry_wraps_sms_with_quota(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SMS_PROVIDER", "mock")
    store = JsonFileStore(base_dir=tmp_path)
    billing = BillingService(store=store, providers={})
    registry = TenantProviderRegistry(
        config_repository=TenantNotificationConfigRepository(store=store),
        billing_service=billing,
    )
    provider = registry.resolve(Channel.SMS, "tenant-registry")
    assert isinstance(provider, QuotaEnforcingSMSProvider)
    ok, _ = provider.send("13800000009", "content")
    assert ok is True
    assert billing.usage_view("tenant-registry").sms_used == 1


def test_subscription_quota_resets_in_new_period(tmp_path) -> None:
    now = datetime(2026, 1, 15, tzinfo=UTC)
    store = JsonFileStore(base_dir=tmp_path)
    billing = BillingService(store=store, providers={}, clock=lambda: now)
    billing.record_sms("tenant-period", 5)
    assert billing.usage_view("tenant-period").sms_used == 5
    later = now + timedelta(days=31)
    billing.clock = lambda: later
    assert billing.usage_view("tenant-period").sms_used == 0
