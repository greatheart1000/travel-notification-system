from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.modules.billing.plans import get_plan
from app.modules.billing.providers import PaymentCreation, PaymentError, epay_sign, epay_verify
from app.modules.billing.service import BillingService


class FakeProvider:
    code = "mock"
    display_name = "测试支付"

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.next_paid = True

    def create_payment(self, **kwargs) -> PaymentCreation:
        self.calls.append(kwargs)
        return PaymentCreation(pay_url=f"https://pay.example/{kwargs['order_no']}")

    def verify_notify(self, params: dict[str, str]):
        if not self.next_paid or params.get("sign") != "valid":
            return None
        return {
            "order_no": params.get("out_trade_no", ""),
            "provider_trade_no": "provider-1",
            "amount_cents": int(params.get("amount_cents", "0")),
            "currency": "CNY",
            "status": "paid",
            "raw": params,
        }


def _service(tmp_path, clock=None):
    from app.modules.integration.persistence import JsonFileStore

    provider = FakeProvider()
    service = BillingService(
        JsonFileStore(base_dir=tmp_path),
        providers={provider.code: provider},
        clock=clock,
    )
    return service, provider


def test_plan_catalog_contains_public_paid_plans(tmp_path) -> None:
    service, _ = _service(tmp_path)
    plans = service.list_plans()
    codes = {plan.code for plan in plans}
    assert {"free", "starter", "growth", "enterprise"} <= codes
    assert "trial" not in codes
    assert get_plan("starter").price_cents == 29900


def test_new_tenant_gets_trial_subscription_and_usage(tmp_path) -> None:
    service, _ = _service(tmp_path)
    subscription = service.get_subscription("tenant-new")
    assert subscription.status == "trialing"
    assert subscription.plan_code == "trial"
    view = service.usage_view("tenant-new")
    assert view.plan.code == "trial"
    assert view.sms_quota == get_plan("trial").sms_quota
    assert view.sms_used == 0
    assert service.record_sms("tenant-new").sms_sent == 1


def test_expired_trial_falls_back_to_free_plan(tmp_path) -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    service, _ = _service(tmp_path, clock=lambda: now)
    service.get_subscription("tenant-x")
    later = now + timedelta(days=15)
    service.clock = lambda: later
    plan, subscription = service.effective_plan("tenant-x")
    assert subscription.status == "expired"
    assert plan.code == "free"


def test_create_order_and_verified_callback_activates_plan(tmp_path) -> None:
    service, provider = _service(tmp_path)
    order = service.create_order("tenant-a", "starter", "mock", created_by="user-1")
    assert order.status == "pending"
    assert order.amount_cents == 29900
    assert order.pay_url.startswith("https://pay.example/")
    assert provider.calls[0]["order_no"] == order.order_no

    result = service.handle_notify(
        "mock",
        {"out_trade_no": order.order_no, "amount_cents": "29900", "sign": "valid"},
    )
    assert result["ok"] is True
    stored = service.get_order("tenant-a", order.order_no)
    assert stored.status == "paid"
    subscription = service.get_subscription("tenant-a")
    assert subscription.plan_code == "starter"
    assert subscription.status == "active"


def test_callback_is_idempotent(tmp_path) -> None:
    service, _ = _service(tmp_path)
    order = service.create_order("tenant-a", "starter", "mock")
    params = {"out_trade_no": order.order_no, "amount_cents": "29900", "sign": "valid"}
    service.handle_notify("mock", params)
    result = service.handle_notify("mock", params)
    assert result["idempotent"] is True
    assert service.get_subscription("tenant-a").plan_code == "starter"


def test_callback_rejects_wrong_amount(tmp_path) -> None:
    service, _ = _service(tmp_path)
    order = service.create_order("tenant-a", "starter", "mock")
    with pytest.raises(PaymentError, match="amount_mismatch"):
        service.handle_notify(
            "mock",
            {"out_trade_no": order.order_no, "amount_cents": "1", "sign": "valid"},
        )


def test_same_plan_renewal_extends_from_current_period_end(tmp_path) -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    service, _ = _service(tmp_path, clock=lambda: now)
    service.activate_plan("tenant-a", "starter")
    first_end = service.get_subscription("tenant-a").current_period_end
    later = now + timedelta(days=10)
    service.clock = lambda: later
    service.activate_plan("tenant-a", "starter")
    second_end = service.get_subscription("tenant-a").current_period_end
    assert second_end > first_end


def test_free_plan_cannot_create_order(tmp_path) -> None:
    service, _ = _service(tmp_path)
    with pytest.raises(ValueError, match="plan_is_free"):
        service.create_order("tenant-a", "free", "mock")


def test_mock_payment_is_refused_in_production(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    service, _ = _service(tmp_path)
    order = service.create_order("tenant-a", "starter", "mock")
    with pytest.raises(PaymentError, match="mock_payment_disabled"):
        service.mark_paid_for_local_test("tenant-a", order.order_no)


def test_verified_callback_can_settle_recently_closed_order(tmp_path) -> None:
    service, _ = _service(tmp_path)
    order = service.create_order("tenant-a", "starter", "mock")
    service.cancel_order("tenant-a", order.order_no)
    assert service.get_order("tenant-a", order.order_no).status == "closed"
    result = service.handle_notify(
        "mock",
        {"out_trade_no": order.order_no, "amount_cents": "29900", "sign": "valid"},
    )
    assert result["ok"] is True
    assert service.get_subscription("tenant-a").plan_code == "starter"


def test_renewal_keeps_period_start_and_extends_end(tmp_path) -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    service, _ = _service(tmp_path, clock=lambda: now)
    first = service.activate_plan("tenant-a", "starter")
    later = now + timedelta(days=10)
    service.clock = lambda: later
    second = service.activate_plan("tenant-a", "starter")
    assert second.current_period_start == first.current_period_start
    assert second.current_period_end > first.current_period_end


def test_refund_marks_order_and_can_downgrade(tmp_path) -> None:
    service, _ = _service(tmp_path)
    order = service.create_order("tenant-a", "starter", "mock")
    service.handle_notify(
        "mock",
        {"out_trade_no": order.order_no, "amount_cents": "29900", "sign": "valid"},
    )
    refunded = service.refund_order(order.order_no, downgrade=True)
    assert refunded.status == "refunded"
    assert service.get_subscription("tenant-a").plan_code == "free"


def test_billing_period_uses_business_timezone(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NOTIFICATION_TIMEZONE", "Asia/Shanghai")
    moment = datetime(2026, 1, 31, 16, 30, tzinfo=UTC)  # 2026-02-01 00:30 CST
    service, _ = _service(tmp_path, clock=lambda: moment)
    assert service.usage_view("tenant-a").period == "2026-02"


def test_epay_signature_roundtrip() -> None:
    params = {
        "pid": "2147",
        "out_trade_no": "TN1",
        "money": "299.00",
        "trade_status": "TRADE_SUCCESS",
    }
    sign = epay_sign(params, "secret")
    params["sign"] = sign
    params["sign_type"] = "MD5"
    assert epay_verify(params, "secret") is True
    params["money"] = "0.01"
    assert epay_verify(params, "secret") is False


def test_notify_url_is_provider_specific(monkeypatch) -> None:
    from app.modules.billing.providers import notify_url_for

    monkeypatch.setenv("APP_BASE_URL", "https://app.example.com")
    monkeypatch.setenv(
        "PAYMENT_NOTIFY_URL", "https://app.example.com/api/payments/epay/notify"
    )
    assert notify_url_for("epay") == "https://app.example.com/api/payments/epay/notify"
    assert (
        notify_url_for("jisufu")
        == "https://app.example.com/api/payments/jisufu/notify"
    )

    monkeypatch.setenv(
        "PAYMENT_NOTIFY_URL",
        "https://app.example.com/api/payments/{provider}/notify",
    )
    assert notify_url_for("jisufu") == "https://app.example.com/api/payments/jisufu/notify"

    monkeypatch.delenv("PAYMENT_NOTIFY_URL")
    monkeypatch.setenv(
        "PAYMENT_JISUFU_NOTIFY_URL", "https://custom.example.com/jisufu"
    )
    assert notify_url_for("jisufu") == "https://custom.example.com/jisufu"


def test_epay_create_payment_uses_gateway_response() -> None:
    from app.modules.billing.providers import EpayProvider

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"code": 1, "payurl": "https://pay.example/abc", "trade_no": "T1"}

    class FakeHttp:
        def __init__(self):
            self.calls = []

        def post(self, url, data=None):
            self.calls.append((url, data))
            return FakeResponse()

    http = FakeHttp()
    provider = EpayProvider(
        code="epay",
        display_name="易支付",
        base_url="https://xnoo.cn/",
        pid="2147",
        key="secret",
        http_client=http,
    )
    creation = provider.create_payment(
        order_no="TN1",
        amount_cents=29900,
        subject="标准版",
        notify_url="https://app/api/payments/epay/notify",
        return_url="https://app/billing",
    )
    assert creation.pay_url == "https://pay.example/abc"
    assert http.calls[0][0] == "https://xnoo.cn/mapi.php"
    assert http.calls[0][1]["sign"] == epay_sign(http.calls[0][1], "secret")


class RefundProvider(FakeProvider):
    def __init__(self, *, ok: bool = True) -> None:
        super().__init__()
        self.ok = ok
        self.refund_calls: list[dict] = []

    def refund(self, **kwargs):
        from app.modules.billing.providers import RefundResult

        self.refund_calls.append(kwargs)
        if not self.ok:
            raise PaymentError("gateway_declined")
        return RefundResult(ok=True, refund_trade_no="refund-1", message="ok")


def test_manual_refund_records_operational_metadata(tmp_path) -> None:
    from app.modules.integration.persistence import JsonFileStore

    provider = RefundProvider()
    service = BillingService(JsonFileStore(base_dir=tmp_path), providers={provider.code: provider})
    order = service.create_order("tenant-a", "starter", "mock")
    service.handle_notify(
        "mock",
        {"out_trade_no": order.order_no, "amount_cents": "29900", "sign": "valid"},
    )

    refunded = service.refund_order(
        order.order_no,
        mode="manual",
        reason="客户申请退款",
        operator_id="ops-1",
    )

    assert refunded.status == "refunded"
    assert refunded.refund_status == "refunded"
    assert refunded.refund_mode == "manual"
    assert refunded.refund_amount_cents == 29900
    assert refunded.refund_reason == "客户申请退款"
    assert refunded.refunded_by == "ops-1"
    assert refunded.refunded_at


def test_gateway_refund_calls_provider_and_marks_order(tmp_path) -> None:
    from app.modules.integration.persistence import JsonFileStore

    provider = RefundProvider()
    service = BillingService(JsonFileStore(base_dir=tmp_path), providers={provider.code: provider})
    order = service.create_order("tenant-a", "starter", "mock")
    service.handle_notify(
        "mock",
        {"out_trade_no": order.order_no, "amount_cents": "29900", "sign": "valid"},
    )

    refunded = service.refund_order(
        order.order_no,
        mode="gateway",
        reason="duplicate",
        operator_id="ops-1",
    )

    assert refunded.status == "refunded"
    assert refunded.refund_mode == "gateway"
    assert refunded.refund_trade_no == "refund-1"
    assert provider.refund_calls[0]["order_no"] == order.order_no
    assert provider.refund_calls[0]["amount_cents"] == 29900


def test_gateway_refund_failure_keeps_order_paid_and_records_error(tmp_path) -> None:
    from app.modules.integration.persistence import JsonFileStore

    provider = RefundProvider(ok=False)
    service = BillingService(JsonFileStore(base_dir=tmp_path), providers={provider.code: provider})
    order = service.create_order("tenant-a", "starter", "mock")
    service.handle_notify(
        "mock",
        {"out_trade_no": order.order_no, "amount_cents": "29900", "sign": "valid"},
    )

    with pytest.raises(PaymentError):
        service.refund_order(order.order_no, mode="gateway", reason="gateway down")

    stored = service.get_order("tenant-a", order.order_no)
    assert stored is not None
    assert stored.status == "paid"
    assert stored.refund_status == "failed"
    assert stored.refund_error == "gateway_declined"
