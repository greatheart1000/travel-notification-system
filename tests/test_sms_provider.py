from __future__ import annotations

from app.modules.integration.sms_provider import (
    MisconfiguredSMSProvider,
    MockSMSProvider,
    _mask_phone,
    get_sms_provider,
)


def test_mock_sms_provider_returns_success() -> None:
    provider = MockSMSProvider()

    result = provider.send_sms("13800138000", "hello")

    assert result["ok"] is True
    assert result["status"] == "sent"


def test_misconfigured_sms_provider_fails_closed() -> None:
    provider = MisconfiguredSMSProvider()

    result = provider.send_sms("13800138000", "hello")

    assert result["ok"] is False
    assert result["error"] == "sms_provider_not_configured"


def test_get_sms_provider_unknown_type_fails_closed(monkeypatch) -> None:
    monkeypatch.setenv("SMS_PROVIDER", "unknown-provider")

    provider = get_sms_provider()
    result = provider.send_sms("13800138000", "hello")

    assert result["ok"] is False
    assert result["error"] == "unknown_sms_provider:unknown-provider"


def test_get_sms_provider_aliyun_constructs_with_sdk(monkeypatch) -> None:
    monkeypatch.setenv("SMS_PROVIDER", "aliyun")
    monkeypatch.setenv("ALIYUN_SMS_AK", "test-ak")
    monkeypatch.setenv("ALIYUN_SMS_SK", "test-sk")

    from app.modules.integration.sms_provider import AliyunSMSProvider

    provider = get_sms_provider()
    assert isinstance(provider, AliyunSMSProvider)


def test_mask_phone_does_not_expose_full_number() -> None:
    masked = _mask_phone("13800138000")

    assert masked == "138****8000"
    assert "13800138000" not in masked
