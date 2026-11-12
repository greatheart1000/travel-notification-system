from __future__ import annotations

import os
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.observability import metrics
from app.modules.billing.models import (
    PaymentOrder,
    Subscription,
    TenantUsageView,
    UsageCounter,
    now_iso,
)
from app.modules.billing.plans import Plan, get_plan, load_plans
from app.modules.billing.providers import (
    PaymentError,
    PaymentProvider,
    build_payment_registry,
    notify_url_for,
    plan_subject,
    return_url_for,
)
from app.modules.billing.repository import (
    PaymentOrderRepository,
    SubscriptionRepository,
    UsageRepository,
)
from app.modules.integration.persistence import JsonFileStore


def _parse_iso(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


class BillingService:
    """Plans, subscriptions, orders and SMS quota accounting."""

    def __init__(
        self,
        store: JsonFileStore,
        providers: dict[str, PaymentProvider] | None = None,
        *,
        clock: Callable[[], datetime] | None = None,
        app_env: str | None = None,
    ) -> None:
        self.store = store
        self.subscriptions = SubscriptionRepository(store)
        self.orders = PaymentOrderRepository(store)
        self.usage = UsageRepository(store)
        self.clock = clock or (lambda: datetime.now(tz=UTC))
        self.app_env = (
            app_env if app_env is not None else os.getenv("APP_ENV", "dev")
        ).strip().lower()
        self.providers = providers if providers is not None else build_payment_registry()

    # ------------------------------------------------------------------ plans
    def list_plans(self) -> list[Plan]:
        return sorted(
            [plan for plan in load_plans() if plan.is_public],
            key=lambda plan: plan.sort_order,
        )

    def list_payment_methods(self) -> list[dict[str, str]]:
        return [
            {"code": provider.code, "name": provider.display_name}
            for provider in self.providers.values()
        ]

    def provider(self, code: str) -> PaymentProvider | None:
        return self.providers.get(code)

    # ----------------------------------------------------------- subscription
    def _trial_enabled(self) -> bool:
        import os

        return os.getenv("BILLING_TRIAL_ENABLED", "true").strip().lower() not in {
            "0",
            "false",
            "no",
        }

    def ensure_subscription(self, tenant_id: str) -> Subscription:
        existing = self.subscriptions.get(tenant_id)
        if existing is not None:
            return existing
        now = self.clock()
        if self._trial_enabled():
            plan = get_plan("trial")
            if plan is None:  # catalog override without trial plan
                plan = get_plan("free")
            status = "trialing"
        else:
            plan = get_plan("free")
            status = "active"
        if plan is None:
            raise RuntimeError("billing_plan_catalog_missing_free_plan")
        subscription = Subscription(
            tenant_id=tenant_id,
            plan_code=plan.code,
            status=status,
            started_at=now.isoformat(),
            current_period_start=now.isoformat(),
            current_period_end=(now + timedelta(days=plan.period_days)).isoformat(),
            updated_at=now.isoformat(),
        )
        return self.subscriptions.upsert(subscription)

    def get_subscription(self, tenant_id: str) -> Subscription:
        subscription = self.ensure_subscription(tenant_id)
        end = _parse_iso(subscription.current_period_end)
        if subscription.status in {"trialing", "active"} and end is not None and end <= self.clock():
            subscription.status = "expired"
            subscription.updated_at = now_iso()
            self.subscriptions.upsert(subscription)
        return subscription

    def effective_plan(self, tenant_id: str) -> tuple[Plan, Subscription]:
        subscription = self.get_subscription(tenant_id)
        plan = get_plan(subscription.plan_code)
        if subscription.status in {"trialing", "active"} and plan is not None:
            return plan, subscription
        free = get_plan("free")
        if free is None:
            raise RuntimeError("billing_plan_catalog_missing_free_plan")
        return free, subscription

    # ------------------------------------------------------------------ usage
    def _period(self, moment: datetime | None = None) -> str:
        """Return the billing period in the configured business timezone."""
        tz_name = os.getenv("NOTIFICATION_TIMEZONE", "Asia/Shanghai").strip()
        try:
            from zoneinfo import ZoneInfo

            timezone = ZoneInfo(tz_name)
        except Exception:  # noqa: BLE001 - fall back to UTC
            timezone = UTC
        return (moment or self.clock()).astimezone(timezone).strftime("%Y-%m")

    def usage_view(self, tenant_id: str) -> TenantUsageView:
        plan, subscription = self.effective_plan(tenant_id)
        period = self._period()
        counter = self.usage.get(tenant_id, period)
        return TenantUsageView(
            tenant_id=tenant_id,
            plan=plan,
            subscription=subscription,
            period=period,
            sms_used=counter.sms_sent,
        )

    def check_sms_quota(self, tenant_id: str) -> tuple[bool, int]:
        view = self.usage_view(tenant_id)
        return view.sms_remaining > 0, view.sms_remaining

    def record_sms(self, tenant_id: str, count: int = 1) -> UsageCounter:
        period = self._period()
        return self.usage.increment(tenant_id, period, count)

    # ----------------------------------------------------------------- orders
    def _new_order_no(self) -> str:
        stamp = self.clock().strftime("%Y%m%d%H%M%S")
        return f"TN{stamp}{secrets.token_hex(4).upper()}"

    def create_order(
        self,
        tenant_id: str,
        plan_code: str,
        provider_code: str,
        *,
        created_by: str = "",
    ) -> PaymentOrder:
        plan = get_plan(plan_code)
        if plan is None or not plan.is_public:
            raise ValueError(f"unknown_plan:{plan_code}")
        if plan.is_free or plan.price_cents <= 0:
            raise ValueError("plan_is_free")
        provider = self.providers.get(provider_code)
        if provider is None:
            raise ValueError(f"payment_provider_unavailable:{provider_code}")

        self._prune_pending_orders(tenant_id)
        now = self.clock()
        order_no = self._new_order_no()
        order = PaymentOrder(
            order_no=order_no,
            tenant_id=tenant_id,
            plan_code=plan.code,
            amount_cents=plan.price_cents,
            currency=self._currency(),
            provider=provider_code,
            status="pending",
            created_by=created_by,
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
            expires_at=(now + self._order_ttl()).isoformat(),
        )
        try:
            creation = provider.create_payment(
                order_no=order_no,
                amount_cents=plan.price_cents,
                subject=plan_subject(plan),
                notify_url=notify_url_for(provider_code),
                return_url=return_url_for(),
            )
        except PaymentError as exc:
            order.status = "failed"
            order.last_error = str(exc)
            self.orders.upsert(order)
            raise
        order.pay_url = creation.pay_url
        order.provider_trade_no = creation.provider_trade_no
        metrics.inc(
            "billing_orders_created_total",
            provider=provider_code,
            plan_code=plan_code,
        )
        return self.orders.upsert(order)

    def _prune_pending_orders(self, tenant_id: str, keep: int = 4) -> None:
        """Close expired pending orders and cap abandoned pending orders."""
        pending = [
            order
            for order in self.orders.list_by_tenant(tenant_id, limit=200)
            if order.status == "pending"
        ]
        for order in pending:
            self._expire_if_needed(order)
        still_pending = [order for order in pending if order.status == "pending"]
        if len(still_pending) < max(keep, 1):
            return
        still_pending.sort(key=lambda order: order.created_at)
        # Close enough old orders so that adding the new one keeps ``keep``.
        excess = len(still_pending) - max(keep, 1) + 1
        for order in still_pending[:excess]:
            order.status = "closed"
            order.updated_at = now_iso()
            self.orders.upsert(order)

    def _currency(self) -> str:
        import os

        return os.getenv("BILLING_CURRENCY", "CNY").strip().upper() or "CNY"

    def _order_ttl(self) -> timedelta:
        import os

        try:
            minutes = int(os.getenv("BILLING_ORDER_TTL_MINUTES", "30"))
        except ValueError:
            minutes = 30
        return timedelta(minutes=max(minutes, 5))

    def get_order(self, tenant_id: str, order_no: str) -> PaymentOrder | None:
        order = self.orders.get(order_no)
        if order is None or order.tenant_id != tenant_id:
            return None
        self._expire_if_needed(order)
        return order

    def list_orders(self, tenant_id: str, limit: int = 50) -> list[PaymentOrder]:
        orders = self.orders.list_by_tenant(tenant_id, limit=limit)
        for order in orders:
            self._expire_if_needed(order)
        return orders

    def _expire_if_needed(self, order: PaymentOrder) -> None:
        if order.status != "pending":
            return
        expires_at = _parse_iso(order.expires_at)
        if expires_at is not None and expires_at <= self.clock():
            order.status = "closed"
            order.updated_at = now_iso()
            self.orders.upsert(order)

    def cancel_order(self, tenant_id: str, order_no: str) -> PaymentOrder | None:
        order = self.get_order(tenant_id, order_no)
        if order is None:
            return None
        if order.status == "pending":
            order.status = "closed"
            order.updated_at = now_iso()
            self.orders.upsert(order)
        return order

    # -------------------------------------------------------------- callbacks
    def handle_notify(self, provider_code: str, params: dict[str, str]) -> dict[str, Any]:
        provider = self.providers.get(provider_code)
        if provider is None:
            raise PaymentError("payment_provider_unavailable")
        verified = provider.verify_notify(params)
        if verified is None:
            raise PaymentError("invalid_payment_signature")
        return self._settle(provider_code, verified)

    def handle_stripe_webhook(self, raw_body: bytes, signature: str) -> dict[str, Any]:
        provider = self.providers.get("stripe")
        if provider is None or not hasattr(provider, "verify_webhook"):
            raise PaymentError("payment_provider_unavailable")
        verified = provider.verify_webhook(raw_body, signature)  # type: ignore[attr-defined]
        if verified is None:
            raise PaymentError("invalid_payment_signature")
        return self._settle("stripe", verified)

    def _settle(self, provider_code: str, verified: dict[str, Any]) -> dict[str, Any]:
        order_no = str(verified.get("order_no") or "")
        lock_name = f"billing_order:{order_no}"
        acquired = False
        try:
            acquired = self.store.acquire_advisory_lock(lock_name, timeout_seconds=5)
        except Exception:  # noqa: BLE001 - lock is best-effort
            acquired = False
        try:
            order = self.orders.get(order_no)
            if order is None:
                raise PaymentError("order_not_found")
            if order.provider != provider_code:
                raise PaymentError("payment_provider_mismatch")
            if order.status == "paid":
                return {"ok": True, "idempotent": True, "order": order.to_dict()}
            # A gateway may complete a payment slightly after our local TTL
            # closed the order. Never take money without granting the plan.
            if order.status not in {"pending", "closed"}:
                raise PaymentError(f"order_not_payable:{order.status}")
            if int(verified.get("amount_cents") or 0) != order.amount_cents:
                raise PaymentError("amount_mismatch")

            order.status = "paid"
            order.provider_trade_no = str(
                verified.get("provider_trade_no") or order.provider_trade_no
            )
            order.paid_at = now_iso()
            order.updated_at = order.paid_at
            self.orders.upsert(order)
            self.activate_plan(order.tenant_id, order.plan_code, order_no=order.order_no)
            metrics.inc(
                "billing_payments_succeeded_total",
                provider=provider_code,
                plan_code=order.plan_code,
            )
            return {"ok": True, "idempotent": False, "order": order.to_dict()}
        except PaymentError:
            metrics.inc("billing_payments_failed_total", provider=provider_code)
            raise
        finally:
            if acquired:
                try:
                    self.store.release_advisory_lock(lock_name)
                except Exception:  # noqa: BLE001
                    pass

    def mark_paid_for_local_test(self, tenant_id: str, order_no: str) -> dict[str, Any]:
        """Complete a mock order. Refused when APP_ENV=production."""
        if (self.app_env or "").strip().lower() == "production":
            raise PaymentError("mock_payment_disabled")
        order = self.get_order(tenant_id, order_no)
        if order is None:
            raise PaymentError("order_not_found")
        if order.status == "paid":
            return {"ok": True, "idempotent": True, "order": order.to_dict()}
        if order.status != "pending":
            raise PaymentError(f"order_not_payable:{order.status}")
        order.status = "paid"
        order.provider_trade_no = f"mock-{order.order_no}"
        order.paid_at = now_iso()
        order.updated_at = order.paid_at
        self.orders.upsert(order)
        self.activate_plan(tenant_id, order.plan_code, order_no=order.order_no)
        return {"ok": True, "idempotent": False, "order": order.to_dict()}

    def cancel_subscription(self, tenant_id: str) -> Subscription:
        """Cancel at period end (keeps access until the paid period expires)."""
        subscription = self.get_subscription(tenant_id)
        subscription.cancel_at_period_end = True
        subscription.updated_at = now_iso()
        return self.subscriptions.upsert(subscription)

    def resume_subscription(self, tenant_id: str) -> Subscription:
        subscription = self.get_subscription(tenant_id)
        subscription.cancel_at_period_end = False
        subscription.updated_at = now_iso()
        return self.subscriptions.upsert(subscription)

    # ------------------------------------------------------------ activation
    def activate_plan(
        self,
        tenant_id: str,
        plan_code: str,
        *,
        days: int | None = None,
        order_no: str = "",
    ) -> Subscription:
        plan = get_plan(plan_code)
        if plan is None:
            raise ValueError(f"unknown_plan:{plan_code}")
        lock_name = f"billing_subscription:{tenant_id}"
        acquired = False
        try:
            acquired = self.store.acquire_advisory_lock(lock_name, timeout_seconds=5)
        except Exception:  # noqa: BLE001 - lock is best-effort
            acquired = False
        try:
            now = self.clock()
            current = self.subscriptions.get(tenant_id)
            same_plan_renewal = (
                current is not None
                and current.plan_code == plan_code
                and current.status in {"trialing", "active"}
            )
            base = now
            if same_plan_renewal:
                current_end = _parse_iso(current.current_period_end)
                if current_end is not None and current_end > now:
                    base = current_end
            period_days = days if days is not None else plan.period_days
            subscription = Subscription(
                tenant_id=tenant_id,
                plan_code=plan_code,
                status="active",
                started_at=(
                    current.started_at if same_plan_renewal and current else now.isoformat()
                ),
                current_period_start=(
                    current.current_period_start
                    if same_plan_renewal and current
                    else now.isoformat()
                ),
                current_period_end=(base + timedelta(days=period_days)).isoformat(),
                updated_at=now.isoformat(),
                last_order_no=order_no,
            )
            return self.subscriptions.upsert(subscription)
        finally:
            if acquired:
                try:
                    self.store.release_advisory_lock(lock_name)
                except Exception:  # noqa: BLE001
                    pass

    # -------------------------------------------------------------- operator
    def refund_order(
        self,
        order_no: str,
        *,
        downgrade: bool = False,
    ) -> PaymentOrder:
        """Record a refund. Providers are refunded out-of-band by an operator."""
        order = self.orders.get(order_no)
        if order is None:
            raise PaymentError("order_not_found")
        if order.status != "paid":
            raise PaymentError(f"order_not_refundable:{order.status}")
        order.status = "refunded"
        order.updated_at = now_iso()
        self.orders.upsert(order)
        metrics.inc("billing_orders_refunded_total")
        if downgrade:
            self.activate_plan(order.tenant_id, "free")
        return order

    def overview(self) -> dict[str, Any]:
        period = self._period()
        subscriptions = [
            item for item in self.subscriptions.list_all() if item.tenant_id != "platform"
        ]
        orders = [
            order
            for order in self.orders.list_all(limit=1000)
            if order.tenant_id != "platform"
        ]
        paid_orders = [order for order in orders if order.status == "paid"]
        revenue_cents = sum(order.amount_cents for order in paid_orders)
        period_revenue_cents = 0
        for order in paid_orders:
            paid_at = _parse_iso(order.paid_at)
            if paid_at is not None and self._period(paid_at) == period:
                period_revenue_cents += order.amount_cents
        usage_rows = self.usage.list_period(period)
        active = [
            sub
            for sub in subscriptions
            if sub.status in {"active", "trialing"}
            and (_parse_iso(sub.current_period_end) or datetime.min.replace(tzinfo=UTC))
            > self.clock()
        ]
        return {
            "period": period,
            "tenants": len(subscriptions),
            "active_subscriptions": len(active),
            "paid_orders": len(paid_orders),
            "revenue_cents": revenue_cents,
            "revenue_cents_total": revenue_cents,
            "revenue_cents_this_period": period_revenue_cents,
            "sms_used_this_period": sum(int(row.get("sms_sent") or 0) for row in usage_rows),
            "orders": [order.to_dict() for order in orders],
        }
