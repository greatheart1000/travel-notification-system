from __future__ import annotations

from pathlib import Path

from app.modules.integration.wechat_provider import (
    WeChatWorkWebhookProvider,
    get_wechat_provider_for_trip,
)


def test_repository_contains_no_hardcoded_wecom_webhook_key() -> None:
    src = Path(__file__).resolve().parents[1] / "src"
    content = "\n".join(path.read_text(encoding="utf-8") for path in src.rglob("*.py"))
    assert "5caf181b-1b65-4c28-8e68-e2f8788df1fc" not in content
    assert "WECHAT_WEBHOOK_URL\",\n    \"https://qyapi.weixin.qq.com" not in content


def test_wechat_provider_fails_closed_without_webhook(monkeypatch) -> None:
    from app.modules.integration import wechat_provider

    monkeypatch.setattr(wechat_provider, "WECHAT_WEBHOOK_URL", "")
    monkeypatch.delenv("WECHAT_WEBHOOK_URL", raising=False)
    provider = WeChatWorkWebhookProvider()

    ok, message = provider.send("customer-1", "hello")

    assert ok is False
    assert message == "wechat_webhook_not_configured"


def test_wechat_provider_rejects_non_official_webhook() -> None:
    provider = WeChatWorkWebhookProvider(webhook_url="https://evil.example/webhook?key=x")

    ok, message = provider.send("customer-1", "hello")

    assert ok is False
    assert message == "invalid_webhook_url"


def test_wechat_provider_uses_trip_webhook_from_context() -> None:
    provider = WeChatWorkWebhookProvider(webhook_url="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=default")
    captured: dict[str, str] = {}

    def fake_do_send(customer_id: str, content: str, webhook_url: str) -> tuple[bool, str]:
        captured["url"] = webhook_url
        return True, "ok"

    provider._do_send = fake_do_send  # type: ignore[method-assign]
    ok, _ = provider.send(
        "customer-1",
        "hello",
        {"webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=trip"},
    )

    assert ok is True
    assert captured["url"].endswith("key=trip")


def test_wechat_provider_accepts_official_webhook() -> None:
    provider = WeChatWorkWebhookProvider(
        webhook_url="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=abc"
    )
    assert provider.webhook_url.endswith("key=abc")


def test_wechat_provider_for_trip_prefers_trip_webhook() -> None:
    provider = get_wechat_provider_for_trip(
        {"webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=trip"}
    )

    assert provider.webhook_url.endswith("key=trip")


def test_sms_provider_fails_closed_when_not_configured(monkeypatch) -> None:
    from app.modules.integration import sms_provider

    monkeypatch.delenv("SMS_PROVIDER", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)

    provider = sms_provider.get_sms_provider()
    result = provider.send_sms("13800138000", "hello")

    assert result["ok"] is False
    assert result["error"] == "sms_provider_not_configured"
