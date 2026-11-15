from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.modules.billing.models import Subscription
from app.modules.billing.plans import get_plan
from app.modules.billing.service import BillingService
from app.modules.identity.models import Tenant
from app.modules.identity.repository import TenantRepository
from app.modules.integration.email_provider import EmailProvider
from app.modules.integration.persistence import JsonFileStore

logger = logging.getLogger(__name__)

DEFAULT_DAYS = (7, 3, 1)


def _parse_iso(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _days_before() -> list[int]:
    raw = os.getenv("BILLING_DUNNING_DAYS", "7,3,1")
    values: list[int] = []
    for token in raw.split(","):
        try:
            value = int(token.strip())
        except ValueError:
            continue
        if 1 <= value <= 60 and value not in values:
            values.append(value)
    return sorted(values, reverse=True) or list(DEFAULT_DAYS)


@dataclass(slots=True)
class BillingDunningService:
    """Send subscription expiry reminders to the tenant billing contact.

    Reminders are keyed by (tenant, period_end, days_before) so reruns are
    idempotent. The service never sends when no email provider is configured.
    """

    billing_service: BillingService
    tenant_repository: TenantRepository
    store: JsonFileStore
    email_provider: EmailProvider | None = None
    base_url: str = ""
    collection: str = "billing_dunning_log"
    _sent: set[str] = field(default_factory=set, init=False)

    def __post_init__(self) -> None:
        self.base_url = (self.base_url or os.getenv("APP_BASE_URL", "")).rstrip("/")
        for row in self.store.read_collection(self.collection):
            key = str(row.get("key") or "")
            if key:
                self._sent.add(key)

    def _enabled(self) -> bool:
        return os.getenv("BILLING_DUNNING_ENABLED", "false").strip().lower() not in {
            "0",
            "false",
            "no",
        }

    def _recipient(self, tenant: Tenant | None) -> str:
        if tenant is None:
            return ""
        return (tenant.invoice_email or tenant.contact_email).strip()

    def _compose(
        self,
        tenant: Tenant,
        subscription: Subscription,
        end: datetime,
        days_left: int,
    ) -> tuple[str, str]:
        plan = get_plan(subscription.plan_code)
        plan_name = plan.name if plan else subscription.plan_code
        is_trial = subscription.status == "trialing"
        subject = (
            f"【行程管家】试用即将到期提醒（剩余 {days_left} 天）"
            if is_trial
            else f"【行程管家】套餐即将到期提醒（剩余 {days_left} 天）"
        )
        action = (
            f"如需继续使用，请登录 {self.base_url}/billing 选择套餐。"
            if self.base_url
            else "如需继续使用，请登录系统前往「套餐与账单」选择套餐。"
        )
        quota = f"{plan.sms_quota:,} 条" if plan else "按套餐配置"
        body = (
            f"{tenant.name or tenant.id} 您好：\n\n"
            f"{'试用' if is_trial else plan_name} 将于 {end.date().isoformat()} 到期"
            f"（剩余 {days_left} 天）。\n"
            f"当前套餐：{plan_name}，短信额度：{quota}/周期。\n\n"
            f"{action}\n"
            "如果已经续费，请忽略此邮件。\n\n"
            "—— 行程管家"
        )
        return subject, body

    def run(self, now: datetime | None = None) -> dict[str, Any]:
        if not self._enabled():
            return {"enabled": False, "checked": 0, "sent": 0, "skipped": 0, "failed": 0}
        summary = {"enabled": True, "checked": 0, "sent": 0, "skipped": 0, "failed": 0}
        if self.email_provider is None:
            summary["skipped"] = 1
            summary["reason"] = "email_provider_not_configured"
            return summary

        current = now or datetime.now(tz=UTC)
        days_options = _days_before()
        for subscription in self.billing_service.subscriptions.list_all():
            if subscription.tenant_id == "platform":
                continue
            if subscription.cancel_at_period_end:
                continue
            if subscription.status not in {"trialing", "active"}:
                continue
            plan = get_plan(subscription.plan_code)
            if subscription.status == "active" and (plan is None or plan.is_free):
                continue
            end = _parse_iso(subscription.current_period_end)
            if end is None:
                continue
            days_left = (end.date() - current.date()).days
            matched = next((days for days in days_options if days == days_left), None)
            if matched is None:
                continue

            summary["checked"] += 1
            key = f"{subscription.tenant_id}:{subscription.current_period_end}:{matched}"
            if key in self._sent:
                summary["skipped"] += 1
                continue
            tenant = self.tenant_repository.get(subscription.tenant_id)
            recipient = self._recipient(tenant)
            if tenant is None or not recipient:
                summary["skipped"] += 1
                continue

            subject, body = self._compose(tenant, subscription, end, matched)
            if not self.email_provider.send(recipient, subject, body):
                summary["failed"] += 1
                logger.warning("dunning email failed for tenant=%s", subscription.tenant_id)
                continue

            self._sent.add(key)
            self.store.upsert(
                self.collection,
                {
                    "key": key,
                    "tenant_id": subscription.tenant_id,
                    "period_end": subscription.current_period_end,
                    "days_before": matched,
                    "recipient": recipient,
                    "sent_at": current.isoformat(),
                },
                key="key",
            )
            summary["sent"] += 1
        return summary
