from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.parse import urlencode

import httpx

from app.modules.billing.plans import Plan


class PaymentError(RuntimeError):
    """Raised when a payment provider rejects a request or callback."""


@dataclass(slots=True)
class PaymentCreation:
    pay_url: str
    provider_trade_no: str = ""
    qr_code: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


class PaymentProvider(Protocol):
    code: str
    display_name: str

    def create_payment(
        self,
        *,
        order_no: str,
        amount_cents: int,
        subject: str,
        notify_url: str,
        return_url: str,
    ) -> PaymentCreation:
        """Create a hosted payment and return the redirect/QR target."""

    def verify_notify(self, params: dict[str, str]) -> dict[str, Any] | None:
        """Verify a form/query callback. Return normalized payment facts or None."""


def epay_sign(params: dict[str, Any], merchant_key: str) -> str:
    """Sign parameters the way 彩虹易支付 compatible gateways expect (MD5)."""
    filtered = {
        key: value
        for key, value in params.items()
        if key not in {"sign", "sign_type"} and value not in (None, "")
    }
    canonical = "&".join(f"{key}={filtered[key]}" for key in sorted(filtered))
    return hashlib.md5(f"{canonical}{merchant_key}".encode()).hexdigest()


def epay_verify(params: dict[str, Any], merchant_key: str) -> bool:
    supplied = str(params.get("sign") or "")
    if not supplied:
        return False
    return hmac.compare_digest(supplied.lower(), epay_sign(params, merchant_key).lower())


@dataclass(slots=True)
class EpayProvider:
    """Adapter for 易支付 / 极速付 (彩虹易支付 protocol).

    Both gateways expose the same ``mapi.php`` API and MD5 signature scheme;
    only base URL, merchant id and key differ.
    """

    code: str
    display_name: str
    base_url: str
    pid: str
    key: str
    default_type: str = "alipay"
    http_client: Any | None = None

    def _url(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

    def _client(self) -> Any:
        if self.http_client is not None:
            return self.http_client
        return httpx.Client(timeout=httpx.Timeout(15.0))

    def create_payment(
        self,
        *,
        order_no: str,
        amount_cents: int,
        subject: str,
        notify_url: str,
        return_url: str,
    ) -> PaymentCreation:
        params: dict[str, Any] = {
            "pid": self.pid,
            "type": self.default_type,
            "out_trade_no": order_no,
            "notify_url": notify_url,
            "return_url": return_url,
            "name": subject[:120],
            "money": f"{amount_cents / 100:.2f}",
        }
        params["sign"] = epay_sign(params, self.key)
        params["sign_type"] = "MD5"
        client = self._client()
        try:
            response = client.post(self._url("mapi.php"), data=params)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # noqa: BLE001 - normalized for the caller
            raise PaymentError(f"payment_gateway_unreachable:{type(exc).__name__}") from exc

        if str(payload.get("code")) not in {"1", "200"}:
            raise PaymentError(str(payload.get("msg") or payload.get("message") or "payment_failed"))

        pay_url = (
            str(payload.get("payurl") or payload.get("url") or payload.get("qrcode") or "").strip()
        )
        if not pay_url:
            raise PaymentError("payment_gateway_missing_pay_url")
        return PaymentCreation(
            pay_url=pay_url,
            provider_trade_no=str(payload.get("trade_no") or ""),
            qr_code=str(payload.get("qrcode") or ""),
            raw=payload,
        )

    def verify_notify(self, params: dict[str, str]) -> dict[str, Any] | None:
        if not epay_verify(params, self.key):
            return None
        if str(params.get("pid") or "") != self.pid:
            return None
        status = str(params.get("trade_status") or "")
        if status not in {"TRADE_SUCCESS", "TRADE_FINISHED"}:
            return None
        try:
            amount_cents = int(round(float(str(params.get("money") or "0")) * 100))
        except (TypeError, ValueError):
            return None
        return {
            "order_no": str(params.get("out_trade_no") or ""),
            "provider_trade_no": str(params.get("trade_no") or ""),
            "amount_cents": amount_cents,
            "currency": "CNY",
            "status": "paid",
            "raw": dict(params),
        }


@dataclass(slots=True)
class StripeProvider:
    code: str
    display_name: str
    secret_key: str
    webhook_secret: str = ""
    currency: str = "cny"
    http_client: Any | None = None

    def _client(self) -> Any:
        if self.http_client is not None:
            return self.http_client
        return httpx.Client(timeout=httpx.Timeout(20.0))

    def create_payment(
        self,
        *,
        order_no: str,
        amount_cents: int,
        subject: str,
        notify_url: str,
        return_url: str,
    ) -> PaymentCreation:
        data = {
            "mode": "payment",
            "success_url": _env("STRIPE_SUCCESS_URL") or return_url,
            "cancel_url": _env("STRIPE_CANCEL_URL") or return_url,
            "client_reference_id": order_no,
            "line_items[0][quantity]": "1",
            "line_items[0][price_data][currency]": self.currency,
            "line_items[0][price_data][unit_amount]": str(amount_cents),
            "line_items[0][price_data][product_data][name]": subject,
            "metadata[order_no]": order_no,
        }
        client = self._client()
        try:
            response = client.post(
                "https://api.stripe.com/v1/checkout/sessions",
                data=data,
                headers={"Authorization": f"Bearer {self.secret_key}"},
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # noqa: BLE001
            raise PaymentError(f"stripe_unreachable:{type(exc).__name__}") from exc
        url = str(payload.get("url") or "")
        if not url:
            raise PaymentError("stripe_missing_checkout_url")
        return PaymentCreation(pay_url=url, provider_trade_no=str(payload.get("id") or ""), raw=payload)

    def verify_notify(self, params: dict[str, str]) -> dict[str, Any] | None:
        # Stripe callbacks are signed against the raw body, not form fields.
        return None

    def verify_webhook(self, raw_body: bytes, signature_header: str) -> dict[str, Any] | None:
        if not self.webhook_secret:
            return None
        parts: dict[str, list[str]] = {}
        for part in (signature_header or "").split(","):
            key, _, value = part.partition("=")
            parts.setdefault(key.strip(), []).append(value.strip())
        try:
            timestamp = int(parts.get("t", ["0"])[0])
        except ValueError:
            return None
        if abs(time.time() - timestamp) > 300:
            return None
        expected = hmac.new(
            self.webhook_secret.encode("utf-8"),
            f"{timestamp}.".encode() + raw_body,
            hashlib.sha256,
        ).hexdigest()
        if not any(
            hmac.compare_digest(expected, supplied) for supplied in parts.get("v1", [])
        ):
            return None
        try:
            event = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        if str(event.get("type") or "") != "checkout.session.completed":
            return None
        session = ((event.get("data") or {}).get("object") or {})
        order_no = str(
            ((session.get("metadata") or {}).get("order_no"))
            or session.get("client_reference_id")
            or ""
        )
        if not order_no:
            return None
        return {
            "order_no": order_no,
            "provider_trade_no": str(session.get("payment_intent") or session.get("id") or ""),
            "amount_cents": int(session.get("amount_total") or 0),
            "currency": str(session.get("currency") or self.currency).upper(),
            "status": "paid",
            "raw": event,
        }


@dataclass(slots=True)
class MockPaymentProvider:
    """Local-only provider used for smoke tests. Never enabled in production."""

    code: str = "mock"
    display_name: str = "模拟支付（仅开发环境）"

    def create_payment(
        self,
        *,
        order_no: str,
        amount_cents: int,
        subject: str,
        notify_url: str,
        return_url: str,
    ) -> PaymentCreation:
        return PaymentCreation(
            pay_url=f"/billing?mock_order={order_no}",
            provider_trade_no=f"mock-{order_no}",
            raw={"mode": "mock"},
        )

    def verify_notify(self, params: dict[str, str]) -> dict[str, Any] | None:
        # Mock payments are completed through an authenticated dev endpoint.
        return None


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def build_payment_registry(app_env: str | None = None) -> dict[str, PaymentProvider]:
    """Build providers from environment. Incomplete configs are skipped."""
    environment = (app_env or os.getenv("APP_ENV", "dev")).strip().lower()
    requested = [
        item.strip().lower()
        for item in _env("PAYMENT_PROVIDERS", "epay,jisufu").split(",")
        if item.strip()
    ]
    providers: dict[str, PaymentProvider] = {}

    epay_base = _env("PAYMENT_EPAY_BASE_URL")
    epay_pid = _env("PAYMENT_EPAY_PID")
    epay_key = _env("PAYMENT_EPAY_KEY")
    if epay_base and epay_pid and epay_key and "epay" in requested:
        providers["epay"] = EpayProvider(
            code="epay",
            display_name="支付宝 / 微信支付",
            base_url=epay_base,
            pid=epay_pid,
            key=epay_key,
            default_type=_env("PAYMENT_EPAY_TYPE", "alipay") or "alipay",
        )

    jisufu_base = _env("PAYMENT_JISUFU_BASE_URL")
    jisufu_pid = _env("PAYMENT_JISUFU_PID")
    jisufu_key = _env("PAYMENT_JISUFU_KEY")
    if jisufu_base and jisufu_pid and jisufu_key and "jisufu" in requested:
        providers["jisufu"] = EpayProvider(
            code="jisufu",
            display_name="极速付",
            base_url=jisufu_base,
            pid=jisufu_pid,
            key=jisufu_key,
            default_type=_env("PAYMENT_JISUFU_TYPE", "alipay") or "alipay",
        )

    stripe_key = _env("STRIPE_SECRET_KEY")
    if stripe_key and "stripe" in requested:
        providers["stripe"] = StripeProvider(
            code="stripe",
            display_name="Stripe",
            secret_key=stripe_key,
            webhook_secret=_env("STRIPE_WEBHOOK_SECRET"),
            currency=_env("BILLING_CURRENCY", "CNY").lower(),
        )

    if environment != "production" and ("mock" in requested or not providers):
        providers["mock"] = MockPaymentProvider()

    return providers


def notify_url_for(provider_code: str) -> str:
    provider_specific = _env(f"PAYMENT_{provider_code.upper()}_NOTIFY_URL")
    if provider_specific:
        return provider_specific
    generic = _env("PAYMENT_NOTIFY_URL")
    if generic:
        if "{provider}" in generic:
            return generic.replace("{provider}", provider_code)
        # Only accept a generic URL that already targets this provider;
        # otherwise return to the canonical per-provider endpoint.
        if f"/{provider_code}/" in generic:
            return generic
    base = _env("APP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    return f"{base}/api/payments/{provider_code}/notify"


def return_url_for() -> str:
    configured = _env("PAYMENT_RETURN_URL")
    if configured:
        return configured
    base = _env("APP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    return f"{base}/billing"


def form_encode(params: dict[str, Any]) -> str:
    return urlencode({key: value for key, value in params.items() if value is not None})


def plan_subject(plan: Plan) -> str:
    return f"行程管家 {plan.name}（{plan.period_days} 天）"
