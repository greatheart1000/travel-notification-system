from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.modules.billing.models import PaymentOrder, Subscription, UsageCounter
from app.modules.integration.persistence import JsonFileStore


@dataclass(slots=True)
class SubscriptionRepository:
    store: JsonFileStore
    collection: str = "billing_subscriptions"

    def get(self, tenant_id: str) -> Subscription | None:
        for item in self.store.read_collection(self.collection):
            if str(item.get("tenant_id") or "") == tenant_id:
                return Subscription.from_dict(item)
        return None

    def upsert(self, subscription: Subscription) -> Subscription:
        self.store.upsert(self.collection, subscription.to_dict(), key="tenant_id")
        return subscription

    def list_all(self) -> list[Subscription]:
        return [Subscription.from_dict(item) for item in self.store.read_collection(self.collection)]


@dataclass(slots=True)
class PaymentOrderRepository:
    store: JsonFileStore
    collection: str = "billing_orders"

    def get(self, order_no: str) -> PaymentOrder | None:
        for item in self.store.read_collection(self.collection):
            if str(item.get("order_no") or item.get("id") or "") == order_no:
                return PaymentOrder.from_dict(item)
        return None

    def upsert(self, order: PaymentOrder) -> PaymentOrder:
        self.store.upsert(self.collection, order.to_dict(), key="order_no")
        return order

    def list_by_tenant(self, tenant_id: str, limit: int = 50) -> list[PaymentOrder]:
        items = [
            PaymentOrder.from_dict(item)
            for item in self.store.read_collection(self.collection)
            if str(item.get("tenant_id") or "") == tenant_id
        ]
        items.sort(key=lambda order: order.created_at, reverse=True)
        return items[: max(1, min(limit, 200))]

    def list_all(self, limit: int = 200) -> list[PaymentOrder]:
        items = [PaymentOrder.from_dict(item) for item in self.store.read_collection(self.collection)]
        items.sort(key=lambda order: order.created_at, reverse=True)
        return items[: max(1, min(limit, 1000))]


@dataclass(slots=True)
class UsageRepository:
    store: JsonFileStore
    collection: str = "billing_usage"

    def get(self, tenant_id: str, period: str) -> UsageCounter:
        key = f"{tenant_id}:{period}"
        for item in self.store.read_collection(self.collection):
            if str(item.get("id") or "") == key:
                return UsageCounter.from_dict(item)
        return UsageCounter(tenant_id=tenant_id, period=period)

    def increment(self, tenant_id: str, period: str, amount: int = 1) -> UsageCounter:
        lock_name = f"billing_usage:{tenant_id}:{period}"
        acquired = False
        try:
            acquired = self.store.acquire_advisory_lock(lock_name, timeout_seconds=2)
        except Exception:  # noqa: BLE001 - lock is best-effort
            acquired = False
        try:
            counter = self.get(tenant_id, period)
            counter.sms_sent += max(amount, 0)
            from app.modules.billing.models import now_iso

            counter.updated_at = now_iso()
            self.store.upsert(self.collection, counter.to_dict(), key="id")
            return counter
        finally:
            if acquired:
                try:
                    self.store.release_advisory_lock(lock_name)
                except Exception:  # noqa: BLE001
                    pass

    def list_period(self, period: str) -> list[dict[str, Any]]:
        return [
            item
            for item in self.store.read_collection(self.collection)
            if str(item.get("period") or "") == period
        ]
