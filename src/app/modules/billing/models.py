from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.modules.billing.plans import Plan


def now_iso() -> str:
    from datetime import UTC

    return datetime.now(tz=UTC).isoformat()


@dataclass(slots=True)
class Subscription:
    tenant_id: str
    plan_code: str
    status: str  # trialing | active | expired | cancelled
    started_at: str
    current_period_start: str
    current_period_end: str
    cancel_at_period_end: bool = False
    updated_at: str = ""
    last_order_no: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.tenant_id,
            "tenant_id": self.tenant_id,
            "plan_code": self.plan_code,
            "status": self.status,
            "started_at": self.started_at,
            "current_period_start": self.current_period_start,
            "current_period_end": self.current_period_end,
            "cancel_at_period_end": self.cancel_at_period_end,
            "updated_at": self.updated_at or now_iso(),
            "last_order_no": self.last_order_no,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Subscription:
        return cls(
            tenant_id=str(raw.get("tenant_id") or ""),
            plan_code=str(raw.get("plan_code") or "free"),
            status=str(raw.get("status") or "expired"),
            started_at=str(raw.get("started_at") or ""),
            current_period_start=str(raw.get("current_period_start") or ""),
            current_period_end=str(raw.get("current_period_end") or ""),
            cancel_at_period_end=bool(raw.get("cancel_at_period_end", False)),
            updated_at=str(raw.get("updated_at") or ""),
            last_order_no=str(raw.get("last_order_no") or ""),
        )


@dataclass(slots=True)
class PaymentOrder:
    order_no: str
    tenant_id: str
    plan_code: str
    amount_cents: int
    currency: str
    provider: str
    status: str  # pending | paid | closed | refunded | failed
    pay_url: str = ""
    provider_trade_no: str = ""
    created_by: str = ""
    created_at: str = ""
    updated_at: str = ""
    paid_at: str = ""
    expires_at: str = ""
    last_error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.order_no,
            "order_no": self.order_no,
            "tenant_id": self.tenant_id,
            "plan_code": self.plan_code,
            "amount_cents": self.amount_cents,
            "currency": self.currency,
            "provider": self.provider,
            "status": self.status,
            "pay_url": self.pay_url,
            "provider_trade_no": self.provider_trade_no,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "paid_at": self.paid_at,
            "expires_at": self.expires_at,
            "last_error": self.last_error,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> PaymentOrder:
        return cls(
            order_no=str(raw.get("order_no") or raw.get("id") or ""),
            tenant_id=str(raw.get("tenant_id") or ""),
            plan_code=str(raw.get("plan_code") or ""),
            amount_cents=int(raw.get("amount_cents") or 0),
            currency=str(raw.get("currency") or "CNY"),
            provider=str(raw.get("provider") or ""),
            status=str(raw.get("status") or "pending"),
            pay_url=str(raw.get("pay_url") or ""),
            provider_trade_no=str(raw.get("provider_trade_no") or ""),
            created_by=str(raw.get("created_by") or ""),
            created_at=str(raw.get("created_at") or ""),
            updated_at=str(raw.get("updated_at") or ""),
            paid_at=str(raw.get("paid_at") or ""),
            expires_at=str(raw.get("expires_at") or ""),
            last_error=str(raw.get("last_error") or ""),
        )


@dataclass(slots=True)
class UsageCounter:
    tenant_id: str
    period: str
    sms_sent: int = 0
    updated_at: str = ""

    @property
    def key(self) -> str:
        return f"{self.tenant_id}:{self.period}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.key,
            "tenant_id": self.tenant_id,
            "period": self.period,
            "sms_sent": self.sms_sent,
            "updated_at": self.updated_at or now_iso(),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> UsageCounter:
        return cls(
            tenant_id=str(raw.get("tenant_id") or ""),
            period=str(raw.get("period") or ""),
            sms_sent=int(raw.get("sms_sent") or 0),
            updated_at=str(raw.get("updated_at") or ""),
        )


@dataclass(slots=True)
class TenantUsageView:
    tenant_id: str
    plan: Plan
    subscription: Subscription
    period: str
    sms_used: int

    @property
    def sms_quota(self) -> int:
        return self.plan.sms_quota

    @property
    def sms_remaining(self) -> int:
        return max(self.plan.sms_quota - self.sms_used, 0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "period": self.period,
            "plan_code": self.plan.code,
            "plan_name": self.plan.name,
            "sms_used": self.sms_used,
            "sms_quota": self.plan.sms_quota,
            "sms_remaining": self.sms_remaining,
            "usage_ratio": round(
                (self.sms_used / self.plan.sms_quota) if self.plan.sms_quota else 0.0, 4
            ),
            "subscription_status": self.subscription.status,
            "current_period_end": self.subscription.current_period_end,
        }
