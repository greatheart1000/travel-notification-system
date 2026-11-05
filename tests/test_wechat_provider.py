from __future__ import annotations

import asyncio
import json
import urllib.error

from app.modules.integration.wechat_provider import WeChatWorkWebhookProvider

OFFICIAL_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test"


class _Response:
    def __init__(self, body: dict) -> None:
        self._body = body

    def read(self) -> bytes:
        return json.dumps(self._body).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_wechat_send_success(monkeypatch) -> None:
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: _Response({"errcode": 0, "errmsg": "ok"}),
    )
    provider = WeChatWorkWebhookProvider(webhook_url=OFFICIAL_URL)

    ok, message = provider.send("customer-1", "hello")

    assert ok is True
    assert message == "ok"


def test_wechat_business_error_is_permanent(monkeypatch) -> None:
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: _Response({"errcode": 93000, "errmsg": "invalid webhook url"}),
    )
    provider = WeChatWorkWebhookProvider(webhook_url=OFFICIAL_URL)

    ok, message = provider.send("customer-1", "hello")

    assert ok is False
    assert message.startswith("wecom_error:")


def test_wechat_url_error_is_retryable(monkeypatch) -> None:
    def raise_url_error(request, timeout):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", raise_url_error)
    provider = WeChatWorkWebhookProvider(webhook_url=OFFICIAL_URL)

    ok, message = provider.send("customer-1", "hello")

    assert ok is False
    assert message.startswith("request_failed:")


def test_wechat_empty_content_does_not_call_network(monkeypatch) -> None:
    called = False

    def fail_if_called(request, timeout):
        nonlocal called
        called = True
        return _Response({"errcode": 0})

    monkeypatch.setattr("urllib.request.urlopen", fail_if_called)
    provider = WeChatWorkWebhookProvider(webhook_url=OFFICIAL_URL)

    ok, message = provider.send("customer-1", "   ")

    assert ok is False
    assert message == "empty_content"
    assert called is False


def test_wechat_send_async(monkeypatch) -> None:
    provider = WeChatWorkWebhookProvider(webhook_url=OFFICIAL_URL)
    provider._do_send = lambda customer_id, content, webhook_url=None: (True, "ok")  # type: ignore[method-assign]

    ok, message = asyncio.run(provider.send_async("customer-1", "hello"))

    assert ok is True
    assert message == "ok"


def test_wechat_official_url_validation_rejects_http() -> None:
    provider = WeChatWorkWebhookProvider(
        webhook_url="http://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test"
    )

    ok, message = provider.send("customer-1", "hello")

    assert ok is False
    assert message == "invalid_webhook_url"
