from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.core.observability import metrics
from app.modules.identity.models import VerificationCode
from app.modules.identity.repository import VerificationCodeRepository
from app.modules.integration.auth import normalize_phone
from app.modules.integration.persistence import JsonFileStore
from app.modules.integration.sms_provider import MockSMSProvider, SMSProvider, get_sms_provider

VALID_PURPOSES = {"login", "register", "reset"}


class VerificationError(Exception):
    def __init__(
        self,
        code: str,
        message: str = "",
        status_code: int = 400,
        *,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code
        self.status_code = status_code
        self.retry_after = retry_after


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass
class VerificationService:
    """Issue and verify SMS one-time codes for login/registration/reset."""

    store: JsonFileStore
    sms_provider: SMSProvider | None = None
    clock: object | None = None
    app_env: str = ""

    def __post_init__(self) -> None:
        self.repository = VerificationCodeRepository(self.store)
        self.environment = (self.app_env or os.getenv("APP_ENV", "dev")).strip().lower()
        self.code_ttl_seconds = _env_int("VERIFICATION_CODE_TTL_SECONDS", 300)
        self.cooldown_seconds = _env_int("VERIFICATION_CODE_COOLDOWN_SECONDS", 60)
        self.daily_limit = _env_int("VERIFICATION_CODE_DAILY_LIMIT", 10)
        self.ip_daily_limit = _env_int("VERIFICATION_CODE_IP_DAILY_LIMIT", 50)
        self.max_attempts = _env_int("VERIFICATION_CODE_MAX_ATTEMPTS", 5)
        self.global_daily_limit = _env_int(
            "VERIFICATION_CODE_GLOBAL_DAILY_LIMIT", 2000
        )

    def _now(self) -> datetime:
        if callable(self.clock):
            return self.clock()  # type: ignore[return-value]
        return datetime.now(tz=UTC)

    def _secret(self) -> bytes:
        secret = os.getenv("VERIFICATION_CODE_SECRET", "").strip()
        if not secret:
            if self.environment == "production":
                raise VerificationError(
                    "verification_misconfigured",
                    "验证码服务未配置签名密钥",
                    500,
                )
            secret = "dev-verification-code-secret"
        return secret.encode("utf-8")

    def _hash_code(self, phone: str, purpose: str, code: str) -> str:
        return hmac.new(
            self._secret(),
            f"{phone}:{purpose}:{code}".encode(),
            hashlib.sha256,
        ).hexdigest()

    def _provider(self) -> SMSProvider:
        return self.sms_provider or get_sms_provider()

    def _template_code(self, purpose: str) -> str:
        mapping = {
            "login": ("ALIYUN_SMS_LOGIN_TEMPLATE_CODE", "SMS_512540357"),
            "register": ("ALIYUN_SMS_REGISTER_TEMPLATE_CODE", "SMS_512500353"),
            "reset": ("ALIYUN_SMS_RESET_TEMPLATE_CODE", "SMS_512540357"),
        }
        env_name, default = mapping[purpose]
        return os.getenv(env_name, default).strip() or default

    def _sign_name(self) -> str:
        return os.getenv("ALIYUN_SMS_SIGN_NAME", "江西锌鑫").strip() or "江西锌鑫"

    def _debug_enabled(self, provider: SMSProvider) -> bool:
        if self.environment in {"production", "prod"}:
            return False
        if isinstance(provider, MockSMSProvider):
            return True
        return (
            os.getenv("VERIFICATION_RETURN_DEBUG_CODE", "false").strip().lower()
            in {"1", "true", "yes"}
        )

    def send_code(
        self,
        phone: str,
        purpose: str,
        *,
        client_ip: str = "",
    ) -> dict[str, object]:
        purpose = str(purpose or "").strip().lower()
        if purpose not in VALID_PURPOSES:
            raise VerificationError("invalid_purpose", "无效的验证码用途", 400)
        normalized = normalize_phone(phone)
        now = self._now()
        since_cooldown = (now - timedelta(seconds=self.cooldown_seconds)).isoformat()
        since_day = (now - timedelta(days=1)).isoformat()

        for existing in self.repository.list_all():
            if (
                existing.phone == normalized
                and not existing.used
                and existing.created_at >= since_cooldown
            ):
                raise VerificationError(
                    "sms_code_cooldown",
                    "验证码发送过于频繁，请稍后再试",
                    429,
                    retry_after=self.cooldown_seconds,
                )
        if self.repository.count_since(phone=normalized, since_iso=since_day) >= self.daily_limit:
            raise VerificationError("sms_daily_limit", "该手机号今日验证码次数已达上限", 429)
        if (
            client_ip
            and self.repository.count_ip_since(client_ip=client_ip, since_iso=since_day)
            >= self.ip_daily_limit
        ):
            raise VerificationError("sms_ip_limit", "当前网络请求过于频繁，请稍后再试", 429)
        if (
            self.global_daily_limit > 0
            and self.repository.count_all_since(since_day) >= self.global_daily_limit
        ):
            raise VerificationError(
                "sms_global_limit",
                "系统今日验证码发送量已达上限，请稍后再试",
                429,
            )

        code = f"{secrets.randbelow(1_000_000):06d}"
        record = VerificationCode(
            id=f"vc-{uuid4().hex}",
            phone=normalized,
            purpose=purpose,
            code_hash=self._hash_code(normalized, purpose, code),
            expires_at=(now + timedelta(seconds=self.code_ttl_seconds)).isoformat(),
            created_at=now.isoformat(),
            client_ip=client_ip,
        )
        self.repository.create(record)

        provider = self._provider()
        try:
            result = provider.send_sms(
                normalized,
                f"您的验证码是 {code}，{self.code_ttl_seconds // 60} 分钟内有效。",
                sign_name=self._sign_name(),
                template_code=self._template_code(purpose),
                template_params={"code": code},
            )
        except Exception as exc:  # noqa: BLE001 - normalized for API callers
            record.used = True
            self.repository.update(record)
            raise VerificationError(
                "sms_send_failed",
                f"短信通道异常：{type(exc).__name__}",
                502,
            ) from exc
        if not result.get("ok"):
            record.used = True
            self.repository.update(record)
            metrics.inc("verification_code_send_failures_total", purpose=purpose)
            raise VerificationError(
                "sms_send_failed",
                str(result.get("error") or "短信发送失败"),
                502,
            )

        metrics.inc("verification_codes_sent_total", purpose=purpose)
        payload: dict[str, object] = {
            "sent": True,
            "expires_in": self.code_ttl_seconds,
            "cooldown": self.cooldown_seconds,
        }
        if self._debug_enabled(provider):
            payload["debug_code"] = code
        return payload

    def verify_code(self, phone: str, code: str, purpose: str) -> bool:
        purpose = str(purpose or "").strip().lower()
        if purpose not in VALID_PURPOSES:
            return False
        try:
            normalized = normalize_phone(phone)
        except Exception:  # noqa: BLE001 - invalid phone means invalid code
            return False
        record = self.repository.latest(normalized, purpose)
        if record is None:
            return False
        now = self._now()
        try:
            expires_at = datetime.fromisoformat(record.expires_at)
        except ValueError:
            record.used = True
            self.repository.update(record)
            return False
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= now:
            record.used = True
            self.repository.update(record)
            return False

        record.attempts += 1
        if record.attempts > self.max_attempts:
            record.used = True
            self.repository.update(record)
            return False

        actual = self._hash_code(normalized, purpose, str(code or "").strip())
        ok = hmac.compare_digest(actual, record.code_hash)
        if ok:
            record.used = True
        else:
            metrics.inc("verification_code_verifications_failed_total", purpose=purpose)
        self.repository.update(record)
        return ok

    def purge_expired(self) -> int:
        """Best-effort cleanup of expired/used codes."""
        removed = 0
        now = self._now()
        for record in self.repository.list_all():
            try:
                expires_at = datetime.fromisoformat(record.expires_at)
            except ValueError:
                expires_at = now
            if record.used or expires_at <= now - timedelta(days=1):
                if self.store.delete(
                    self.repository.collection, record.id, key="id"
                ):
                    removed += 1
        return removed
