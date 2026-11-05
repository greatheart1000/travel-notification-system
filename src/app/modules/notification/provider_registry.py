from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.core.models import Channel
from app.modules.integration.persistence import JsonFileStore
from app.modules.integration.sms_provider import (
    AliyunSMSProvider,
    MisconfiguredSMSProvider,
    MockSMSProvider,
    SMSProvider,
)
from app.modules.integration.wechat_provider import WeChatWorkWebhookProvider


class ChannelProvider(Protocol):
    def send(
        self,
        customer_id: str,
        content: str,
        provider_context: dict[str, str] | None = None,
    ) -> tuple[bool, str]:
        """Return (ok, provider_message)."""


class RealWorldSMSProvider:
    """Adapt SMSProvider to the notification ChannelProvider protocol."""

    _PHONE_PATTERN = re.compile(r"^\+?\d{7,20}$")

    def __init__(self, provider: SMSProvider):
        self.provider = provider

    def send(
        self,
        customer_id: str,
        content: str,
        provider_context: dict[str, str] | None = None,
    ) -> tuple[bool, str]:
        phone = customer_id.strip()
        if not self._PHONE_PATTERN.fullmatch(phone):
            return False, "invalid_phone"
        metadata = provider_context or {}
        result = self.provider.send_sms(
            phone,
            content,
            sign_name=metadata.get("sms_sign_name", "TravelHub"),
            template_code=metadata.get("provider_template_code", ""),
            template_params=metadata.get("template_params"),
        )
        return result["ok"], result.get("msg_id", result.get("error", "unknown"))


@dataclass(slots=True)
class TenantNotificationConfigRepository:
    """Per-tenant channel configuration (no secrets in source code)."""

    store: JsonFileStore
    collection: str = "tenant_notification_configs"

    def list(self) -> list[dict[str, Any]]:
        return list(self.store.read_collection(self.collection))

    def get(self, tenant_id: str) -> dict[str, Any] | None:
        for item in self.store.read_collection(self.collection):
            if str(item.get("tenant_id") or "") == tenant_id:
                return dict(item)
        return None

    def upsert(self, payload: dict[str, Any]) -> dict[str, Any]:
        item = dict(payload)
        tenant_id = str(item.get("tenant_id") or "").strip()
        if not tenant_id:
            raise ValueError("tenant_id is required")
        item["tenant_id"] = tenant_id
        item["wechat_webhook_url"] = str(item.get("wechat_webhook_url") or "")
        item["sms_provider"] = str(item.get("sms_provider") or "")
        item["sms_sign_name"] = str(item.get("sms_sign_name") or "")
        item["sms_template_code"] = str(item.get("sms_template_code") or "")
        # Secrets should be references (e.g. secret-manager ids), not raw keys.
        item["sms_credential_id"] = str(item.get("sms_credential_id") or "")
        item["updated_at"] = str(item.get("updated_at") or "")
        return self.store.upsert(self.collection, item, key="tenant_id")


@dataclass(slots=True)
class TenantProviderRegistry:
    """Resolve channel providers using tenant config, trip context, and env fallback."""

    config_repository: TenantNotificationConfigRepository
    _cache: dict[tuple[str, str, str], ChannelProvider] = field(default_factory=dict)

    def resolve(
        self,
        channel: Channel,
        tenant_id: str,
        provider_context: dict[str, str] | None = None,
    ) -> ChannelProvider | None:
        context = provider_context or {}
        config = self.config_repository.get(tenant_id) or {}
        if channel is Channel.WECHAT_WORK_GROUP:
            webhook = (
                str(context.get("webhook_url") or "").strip()
                or str(config.get("wechat_webhook_url") or "").strip()
                or os.getenv("WECHAT_WEBHOOK_URL", "").strip()
            )
            return WeChatWorkWebhookProvider(webhook_url=webhook or None)
        if channel is Channel.SMS:
            provider_type = str(config.get("sms_provider") or "").strip().lower()
            if not provider_type:
                provider_type = os.getenv("SMS_PROVIDER", "").strip().lower()
            if not provider_type and os.getenv("APP_ENV", "").strip().lower() in {
                "test",
                "dev",
                "local",
            }:
                provider_type = "mock"
            if provider_type == "mock":
                backend: SMSProvider = MockSMSProvider()
            elif provider_type == "aliyun":
                backend = AliyunSMSProvider(
                    access_key_id=str(config.get("sms_access_key_id") or "") or None,
                    access_key_secret=str(config.get("sms_access_key_secret") or "") or None,
                )
            else:
                backend = MisconfiguredSMSProvider(
                    reason=(
                        f"unknown_sms_provider:{provider_type}"
                        if provider_type
                        else "sms_provider_not_configured"
                    )
                )
            return RealWorldSMSProvider(backend)
        return None
