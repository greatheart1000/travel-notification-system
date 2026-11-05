from __future__ import annotations

from app.core.models import Channel
from app.modules.integration.persistence import JsonFileStore
from app.modules.notification.provider_registry import (
    TenantNotificationConfigRepository,
    TenantProviderRegistry,
)


def _registry(json_store: JsonFileStore) -> tuple[TenantProviderRegistry, TenantNotificationConfigRepository]:
    repo = TenantNotificationConfigRepository(store=json_store)
    return TenantProviderRegistry(config_repository=repo), repo


def test_tenant_wechat_webhooks_are_isolated(json_store) -> None:
    registry, repo = _registry(json_store)
    repo.upsert(
        {
            "tenant_id": "tenant-a",
            "wechat_webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=a",
        }
    )
    repo.upsert(
        {
            "tenant_id": "tenant-b",
            "wechat_webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=b",
        }
    )

    provider_a = registry.resolve(Channel.WECHAT_WORK_GROUP, "tenant-a")
    provider_b = registry.resolve(Channel.WECHAT_WORK_GROUP, "tenant-b")

    assert provider_a is not None and provider_a.webhook_url.endswith("key=a")
    assert provider_b is not None and provider_b.webhook_url.endswith("key=b")


def test_tenant_sms_provider_uses_mock_when_configured(json_store) -> None:
    registry, repo = _registry(json_store)
    repo.upsert({"tenant_id": "tenant-a", "sms_provider": "mock"})

    provider = registry.resolve(Channel.SMS, "tenant-a")

    assert provider is not None
    ok, _ = provider.send("13800138000", "hello")
    assert ok is True


def test_missing_sms_configuration_fails_closed(json_store, monkeypatch) -> None:
    monkeypatch.delenv("SMS_PROVIDER", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    registry, _ = _registry(json_store)

    provider = registry.resolve(Channel.SMS, "tenant-a")

    assert provider is not None
    ok, message = provider.send("13800138000", "hello")
    assert ok is False
    assert message == "sms_provider_not_configured"


def test_trip_webhook_context_has_higher_priority(json_store) -> None:
    registry, repo = _registry(json_store)
    repo.upsert(
        {
            "tenant_id": "tenant-a",
            "wechat_webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=tenant",
        }
    )

    provider = registry.resolve(
        Channel.WECHAT_WORK_GROUP,
        "tenant-a",
        {"webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=trip"},
    )

    assert provider is not None
    assert provider.webhook_url.endswith("key=trip")
