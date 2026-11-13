from __future__ import annotations

import os
import re
import secrets
from dataclasses import dataclass
from typing import Any

from app.modules.billing.service import BillingService
from app.modules.identity.models import Tenant, now_iso
from app.modules.identity.repository import TenantRepository
from app.modules.identity.verification import VerificationService
from app.modules.integration.auth import (
    AuthError,
    AuthService,
    app_environment,
    normalize_phone,
)

TENANT_NAME_PATTERN = re.compile(r"^[\w一-龥·（）()\- ]{2,64}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass
class AccountService:
    """Registration, SMS login, password reset and tenant profile management."""

    auth_service: AuthService
    tenant_repository: TenantRepository
    verification_service: VerificationService
    billing_service: BillingService | None = None

    def ensure_bootstrap_tenants(self) -> None:
        default_name = os.getenv("BOOTSTRAP_TENANT_NAME", "月亮旅行").strip() or "月亮旅行"
        bootstrap_tenant_id = os.getenv("BOOTSTRAP_TENANT_ID", "tenant-a").strip() or "tenant-a"
        if self.tenant_repository.get(bootstrap_tenant_id) is None:
            self.tenant_repository.create(
                Tenant(
                    id=bootstrap_tenant_id,
                    name=default_name,
                    created_at=now_iso(),
                    updated_at=now_iso(),
                )
            )
        if app_environment() != "production":
            if self.tenant_repository.get("tenant-b") is None:
                self.tenant_repository.create(
                    Tenant(
                        id="tenant-b",
                        name="合作旅行社",
                        created_at=now_iso(),
                        updated_at=now_iso(),
                    )
                )
        # Ensure every user has a tenant record (covers legacy/manual users).
        for user in self.auth_service.users.values():
            tenant_id = str(user.get("tenant_id") or "")
            existing = self.tenant_repository.get(tenant_id) if tenant_id else None
            if tenant_id and existing is None:
                self.tenant_repository.create(
                    Tenant(
                        id=tenant_id,
                        name="平台运营" if tenant_id == "platform" else f"企业 {tenant_id}",
                        created_at=now_iso(),
                        updated_at=now_iso(),
                    )
                )
            elif tenant_id == "platform" and existing is not None and existing.name != "平台运营":
                self.tenant_repository.update(tenant_id, {"name": "平台运营"})
        if self.billing_service is not None:
            for tenant in self.tenant_repository.list_all():
                if tenant.id == "platform":
                    continue
                self.billing_service.ensure_subscription(tenant.id)

    # ------------------------------------------------------------- registration
    def register(
        self,
        *,
        tenant_name: str,
        username: str,
        password: str,
        phone: str,
        code: str,
    ) -> dict[str, Any]:
        tenant_name = str(tenant_name or "").strip()
        username = str(username or "").strip()
        if not TENANT_NAME_PATTERN.fullmatch(tenant_name):
            raise AuthError("invalid_tenant_name", "企业名称需为 2-64 个字符", 400)
        if username in self.auth_service.users:
            raise AuthError("username_taken", "用户名已存在", 409)
        normalized = normalize_phone(phone)
        if self.auth_service.find_by_phone(normalized) is not None:
            raise AuthError("phone_taken", "该手机号已注册", 409)
        # Validate password before consuming the verification code.
        self.auth_service.validate_password(password)
        if not self.verification_service.verify_code(normalized, code, "register"):
            raise AuthError("invalid_verification_code", "验证码错误或已过期", 400)

        tenant_id = f"tenant-{secrets.token_hex(6)}"
        tenant = self.tenant_repository.create(
            Tenant(
                id=tenant_id,
                name=tenant_name,
                contact_phone=normalized,
                created_at=now_iso(),
                updated_at=now_iso(),
            )
        )
        try:
            profile = self.auth_service.create_user(
                tenant_id=tenant_id,
                username=username,
                password=password,
                phone=normalized,
                role="admin",
            )
        except Exception:
            self.tenant_repository.delete(tenant_id)
            raise
        if self.billing_service is not None:
            self.billing_service.ensure_subscription(tenant_id)
        tokens = self.auth_service.issue_token_pair(username)
        return {
            "tokens": tokens,
            "user": profile,
            "tenant": tenant.to_dict(),
        }

    # ------------------------------------------------------------------- login
    def login_with_sms(self, *, phone: str, code: str) -> dict[str, Any]:
        try:
            normalized = normalize_phone(phone)
        except AuthError as exc:
            raise AuthError("invalid_phone", exc.message, 400) from exc
        if not self.verification_service.verify_code(normalized, code, "login"):
            raise AuthError("invalid_verification_code", "验证码错误或已过期", 400)
        user = self.auth_service.find_by_phone(normalized)
        if user is None:
            raise AuthError("account_not_found", "该手机号尚未注册", 404)
        if str(user.get("status") or "active") != "active":
            raise AuthError("account_disabled", "账号已停用，请联系管理员", 403)
        username = str(user.get("username") or "")
        tokens = self.auth_service.issue_token_pair(username)
        return {"tokens": tokens, "user": self.auth_service.get_user_profile(username)}

    def reset_password(self, *, phone: str, code: str, new_password: str) -> dict[str, Any]:
        try:
            normalized = normalize_phone(phone)
        except AuthError as exc:
            raise AuthError("invalid_phone", exc.message, 400) from exc
        self.auth_service.validate_password(new_password)
        if not self.verification_service.verify_code(normalized, code, "reset"):
            raise AuthError("invalid_verification_code", "验证码错误或已过期", 400)
        user = self.auth_service.find_by_phone(normalized)
        if user is None:
            raise AuthError("account_not_found", "该手机号尚未注册", 404)
        self.auth_service.change_password(str(user["username"]), new_password)
        return {"reset": True}

    # ------------------------------------------------------------- tenant profile
    def get_tenant(self, tenant_id: str) -> Tenant | None:
        return self.tenant_repository.get(tenant_id)

    def update_tenant_profile(self, tenant_id: str, patch: dict[str, Any]) -> Tenant | None:
        if patch.get("contact_phone"):
            patch["contact_phone"] = normalize_phone(str(patch["contact_phone"]))
        if "name" in patch and patch["name"] is not None:
            name = str(patch["name"]).strip()
            if not TENANT_NAME_PATTERN.fullmatch(name):
                raise AuthError("invalid_tenant_name", "企业名称需为 2-64 个字符", 400)
            patch["name"] = name
        if patch.get("contact_email"):
            email = str(patch["contact_email"]).strip()
            if not EMAIL_PATTERN.fullmatch(email):
                raise AuthError("invalid_email", "请输入有效的联系邮箱", 400)
            patch["contact_email"] = email
        if patch.get("invoice_email"):
            invoice_email = str(patch["invoice_email"]).strip()
            if not EMAIL_PATTERN.fullmatch(invoice_email):
                raise AuthError("invalid_invoice_email", "请输入有效的收票邮箱", 400)
            patch["invoice_email"] = invoice_email
        return self.tenant_repository.update(tenant_id, patch)

    def list_tenants(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for tenant in self.tenant_repository.list_all():
            if tenant.id == "platform":
                continue
            item = tenant.to_dict()
            if self.billing_service is not None:
                view = self.billing_service.usage_view(tenant.id)
                item["plan_code"] = view.plan.code
                item["plan_name"] = view.plan.name
                item["subscription_status"] = view.subscription.status
                item["sms_used"] = view.sms_used
                item["sms_quota"] = view.plan.sms_quota
            result.append(item)
        return result
