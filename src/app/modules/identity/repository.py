from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.modules.identity.models import LoginAttempt, Tenant, VerificationCode, now_iso
from app.modules.integration.persistence import JsonFileStore

USER_COLLECTION = "auth_users"
SESSION_COLLECTION = "auth_sessions"
TENANT_COLLECTION = "tenants"
VERIFICATION_COLLECTION = "verification_codes"
LOGIN_ATTEMPT_COLLECTION = "auth_login_attempts"


@dataclass(slots=True)
class UserRepository:
    store: JsonFileStore
    collection: str = USER_COLLECTION

    def list_all(self) -> list[dict[str, Any]]:
        return list(self.store.read_collection(self.collection))

    def get(self, username: str) -> dict[str, Any] | None:
        for item in self.list_all():
            if str(item.get("username") or "") == username:
                return dict(item)
        return None

    def get_by_phone(self, phone: str) -> dict[str, Any] | None:
        for item in self.list_all():
            if str(item.get("phone") or "") == phone:
                return dict(item)
        return None

    def list_by_tenant(self, tenant_id: str) -> list[dict[str, Any]]:
        return [
            dict(item)
            for item in self.list_all()
            if str(item.get("tenant_id") or "") == tenant_id
        ]

    def upsert(self, user: dict[str, Any]) -> dict[str, Any]:
        item = dict(user)
        item["id"] = str(item.get("id") or item.get("username") or "")
        item["updated_at"] = str(item.get("updated_at") or now_iso())
        self.store.upsert(self.collection, item, key="username")
        return item

    def delete(self, username: str) -> bool:
        return self.store.delete(self.collection, username, key="username")


@dataclass(slots=True)
class SessionRepository:
    store: JsonFileStore
    collection: str = SESSION_COLLECTION

    def _list(self) -> list[dict[str, Any]]:
        return list(self.store.read_collection(self.collection))

    def upsert(self, record: dict[str, Any]) -> dict[str, Any]:
        item = dict(record)
        item["updated_at"] = str(item.get("updated_at") or now_iso())
        self.store.upsert(self.collection, item, key="access_token_hash")
        return item

    def get_by_access_hash(self, token_hash: str) -> dict[str, Any] | None:
        for item in self._list():
            if str(item.get("access_token_hash") or "") == token_hash:
                return dict(item)
        return None

    def get_by_refresh_hash(self, token_hash: str) -> dict[str, Any] | None:
        for item in self._list():
            if str(item.get("refresh_token_hash") or "") == token_hash:
                return dict(item)
        return None

    def delete_by_access_hash(self, token_hash: str) -> bool:
        return self.store.delete(self.collection, token_hash, key="access_token_hash")

    def delete_by_refresh_hash(self, token_hash: str) -> int:
        deleted = 0
        for item in self._list():
            if str(item.get("refresh_token_hash") or "") == token_hash:
                if self.delete_by_access_hash(str(item.get("access_token_hash") or "")):
                    deleted += 1
        return deleted

    def delete_for_username(self, username: str) -> int:
        deleted = 0
        for item in self._list():
            if str(item.get("username") or "") == username:
                if self.delete_by_access_hash(str(item.get("access_token_hash") or "")):
                    deleted += 1
        return deleted

    def purge_expired(self, now_iso_value: str) -> int:
        deleted = 0
        for item in self._list():
            if str(item.get("expires_at") or "") <= now_iso_value:
                if self.delete_by_access_hash(str(item.get("access_token_hash") or "")):
                    deleted += 1
        return deleted


@dataclass(slots=True)
class TenantRepository:
    store: JsonFileStore
    collection: str = TENANT_COLLECTION

    def list_all(self) -> list[Tenant]:
        return [Tenant.from_dict(item) for item in self.store.read_collection(self.collection)]

    def get(self, tenant_id: str) -> Tenant | None:
        for item in self.store.read_collection(self.collection):
            if str(item.get("tenant_id") or item.get("id") or "") == tenant_id:
                return Tenant.from_dict(item)
        return None

    def upsert(self, tenant: Tenant) -> Tenant:
        self.store.upsert(self.collection, tenant.to_dict(), key="tenant_id")
        return tenant

    def create(self, tenant: Tenant) -> Tenant:
        if self.get(tenant.id) is not None:
            raise ValueError(f"tenant_exists:{tenant.id}")
        return self.upsert(tenant)

    def update(self, tenant_id: str, patch: dict[str, Any]) -> Tenant | None:
        tenant = self.get(tenant_id)
        if tenant is None:
            return None
        for field_name in ("name", "status", "contact_name", "contact_phone", "contact_email"):
            if field_name in patch and patch[field_name] is not None:
                setattr(tenant, field_name, str(patch[field_name]))
        tenant.updated_at = now_iso()
        return self.upsert(tenant)

    def delete(self, tenant_id: str) -> bool:
        return self.store.delete(self.collection, tenant_id, key="tenant_id")


@dataclass(slots=True)
class VerificationCodeRepository:
    store: JsonFileStore
    collection: str = VERIFICATION_COLLECTION

    def list_all(self) -> list[VerificationCode]:
        return [
            VerificationCode.from_dict(item)
            for item in self.store.read_collection(self.collection)
        ]

    def create(self, record: VerificationCode) -> VerificationCode:
        self.store.upsert(self.collection, record.to_dict(), key="id")
        return record

    def update(self, record: VerificationCode) -> VerificationCode:
        self.store.upsert(self.collection, record.to_dict(), key="id")
        return record

    def latest(self, phone: str, purpose: str) -> VerificationCode | None:
        matches = [
            item
            for item in self.list_all()
            if item.phone == phone and item.purpose == purpose and not item.used
        ]
        if not matches:
            return None
        return max(matches, key=lambda item: item.created_at)

    def count_since(self, *, phone: str, since_iso: str, purpose: str | None = None) -> int:
        return sum(
            1
            for item in self.list_all()
            if item.phone == phone
            and item.created_at >= since_iso
            and (purpose is None or item.purpose == purpose)
        )

    def count_ip_since(self, *, client_ip: str, since_iso: str) -> int:
        if not client_ip:
            return 0
        return sum(
            1
            for item in self.list_all()
            if item.client_ip == client_ip and item.created_at >= since_iso
        )

    def count_all_since(self, since_iso: str) -> int:
        return sum(1 for item in self.list_all() if item.created_at >= since_iso)


@dataclass(slots=True)
class LoginAttemptRepository:
    store: JsonFileStore
    collection: str = LOGIN_ATTEMPT_COLLECTION

    def record(self, attempt: LoginAttempt) -> LoginAttempt:
        self.store.upsert(self.collection, attempt.to_dict(), key="id")
        return attempt

    def count_failures(self, identifier: str, since_iso: str) -> int:
        return sum(
            1
            for raw in self.store.read_collection(self.collection)
            if str(raw.get("identifier") or "") == identifier
            and str(raw.get("created_at") or "") >= since_iso
            and not bool(raw.get("ok", False))
        )

    def count_ip_failures(self, client_ip: str, since_iso: str) -> int:
        if not client_ip:
            return 0
        return sum(
            1
            for raw in self.store.read_collection(self.collection)
            if str(raw.get("client_ip") or "") == client_ip
            and str(raw.get("created_at") or "") >= since_iso
            and not bool(raw.get("ok", False))
        )
