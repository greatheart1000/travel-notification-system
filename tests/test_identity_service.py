from __future__ import annotations

import pytest

from app.modules.identity.repository import TenantRepository
from app.modules.identity.service import AccountService
from app.modules.identity.verification import VerificationError, VerificationService
from app.modules.integration.auth import AuthError, AuthService, normalize_phone
from app.modules.integration.persistence import JsonFileStore
from app.modules.integration.sms_provider import SMSProvider


class FakeSMSProvider(SMSProvider):
    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.fail = False
        self.raise_error = False

    def send_sms(
        self,
        phone,
        content,
        sign_name="TravelHub",
        template_code="",
        template_params=None,
    ):
        if self.raise_error:
            raise RuntimeError("network exploded")
        if self.fail:
            return {"ok": False, "error": "gateway_down"}
        self.sent.append(
            {
                "phone": phone,
                "sign_name": sign_name,
                "template_code": template_code,
                "params": template_params,
            }
        )
        return {"ok": True, "msg_id": "msg-1"}


def _stack(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("VERIFICATION_CODE_SECRET", "test-secret")
    monkeypatch.setenv("VERIFICATION_RETURN_DEBUG_CODE", "true")
    store = JsonFileStore(base_dir=tmp_path)
    sms = FakeSMSProvider()
    verification = VerificationService(store=store, sms_provider=sms)
    auth = AuthService(store=store)
    tenants = TenantRepository(store=store)
    from app.modules.billing.service import BillingService

    billing = BillingService(store=store, providers={})
    account = AccountService(
        auth_service=auth,
        tenant_repository=tenants,
        verification_service=verification,
        billing_service=billing,
    )
    account.ensure_bootstrap_tenants()
    return store, sms, verification, auth, tenants, billing, account


def test_normalize_phone_accepts_common_formats() -> None:
    assert normalize_phone("138 0000 0001") == "13800000001"
    assert normalize_phone("+8613800000001") == "13800000001"
    assert normalize_phone("008613800000001") == "13800000001"
    with pytest.raises(AuthError):
        normalize_phone("12345")


def test_register_creates_tenant_admin_and_trial(tmp_path, monkeypatch) -> None:
    store, sms, verification, auth, tenants, billing, account = _stack(tmp_path, monkeypatch)
    code_result = verification.send_code("13800000001", "register")
    code = code_result["debug_code"]
    assert sms.sent[0]["template_code"] == "SMS_512500353"

    result = account.register(
        tenant_name="测试旅行社",
        username="owner",
        password="secret123",
        phone="13800000001",
        code=code,
    )
    assert result["user"]["role"] == "admin"
    assert result["tenant"]["name"] == "测试旅行社"
    assert result["tokens"]["access_token"].startswith("tk-")
    tenant_id = result["user"]["tenant_id"]
    assert tenants.get(tenant_id) is not None
    assert billing.get_subscription(tenant_id).status == "trialing"
    assert auth.find_by_phone("13800000001")["username"] == "owner"


def test_registration_requires_valid_code(tmp_path, monkeypatch) -> None:
    store, sms, verification, auth, tenants, billing, account = _stack(tmp_path, monkeypatch)
    with pytest.raises(AuthError, match="valid_verification_code|验证码"):
        account.register(
            tenant_name="测试旅行社",
            username="owner2",
            password="secret123",
            phone="13800000002",
            code="000000",
        )


def test_sms_login_and_password_reset(tmp_path, monkeypatch) -> None:
    store, sms, verification, auth, tenants, billing, account = _stack(tmp_path, monkeypatch)
    code = verification.send_code("13800000003", "register")["debug_code"]
    account.register(
        tenant_name="登录测试社",
        username="loginuser",
        password="secret123",
        phone="13800000003",
        code=code,
    )

    login_code = verification.send_code("13800000003", "login")["debug_code"]
    login = account.login_with_sms(phone="13800000003", code=login_code)
    assert login["user"]["username"] == "loginuser"
    assert login["tokens"]["access_token"]

    reset_code = verification.send_code("13800000003", "reset")["debug_code"]
    account.reset_password(
        phone="13800000003",
        code=reset_code,
        new_password="newsecret123",
    )
    assert auth.verify_password("loginuser", "newsecret123") is True
    assert auth.verify_password("loginuser", "secret123") is False


def test_sms_code_cooldown(tmp_path, monkeypatch) -> None:
    store, sms, verification, auth, tenants, billing, account = _stack(tmp_path, monkeypatch)
    verification.send_code("13800000004", "login")
    with pytest.raises(VerificationError) as exc:
        verification.send_code("13800000004", "login")
    assert exc.value.code == "sms_code_cooldown"


def test_sms_send_failure_surfaces_and_code_not_usable(tmp_path, monkeypatch) -> None:
    store, sms, verification, auth, tenants, billing, account = _stack(tmp_path, monkeypatch)
    sms.fail = True
    with pytest.raises(VerificationError) as exc:
        verification.send_code("13800000005", "login")
    assert exc.value.code == "sms_send_failed"
    assert verification.verify_code("13800000005", "123456", "login") is False


def test_sms_provider_exception_is_normalized(tmp_path, monkeypatch) -> None:
    store, sms, verification, auth, tenants, billing, account = _stack(tmp_path, monkeypatch)
    sms.raise_error = True
    with pytest.raises(VerificationError) as exc:
        verification.send_code("13800000007", "login")
    assert exc.value.code == "sms_send_failed"


def test_real_sms_provider_never_returns_debug_code(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.delenv("VERIFICATION_RETURN_DEBUG_CODE", raising=False)
    store = JsonFileStore(base_dir=tmp_path)
    sms = FakeSMSProvider()
    verification = VerificationService(store=store, sms_provider=sms)
    result = verification.send_code("13800000008", "login")
    assert result["sent"] is True
    assert "debug_code" not in result


def test_revoked_sessions_after_password_change(tmp_path, monkeypatch) -> None:
    store, sms, verification, auth, tenants, billing, account = _stack(tmp_path, monkeypatch)
    code = verification.send_code("13800000006", "register")["debug_code"]
    result = account.register(
        tenant_name="会话测试社",
        username="sessionuser",
        password="secret123",
        phone="13800000006",
        code=code,
    )
    token = result["tokens"]["access_token"]
    assert auth.authenticate(token) is not None
    auth.change_password("sessionuser", "another123")
    assert auth.authenticate(token) is None


def test_login_rate_limit_counts_failures(tmp_path, monkeypatch) -> None:
    store, sms, verification, auth, tenants, billing, account = _stack(tmp_path, monkeypatch)
    for _ in range(5):
        assert auth.login("admin", "wrong-password", client_ip="1.2.3.4") is None
    assert auth.login_rate_limited("admin", client_ip="1.2.3.4") is True
