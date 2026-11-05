from __future__ import annotations

import pytest

from app.core.models import Channel
from app.modules.integration.sms_provider import MockSMSProvider
from app.modules.notification.idempotency import IdempotencyStore
from app.modules.notification.models import DispatchStatus, NotificationTask
from app.modules.notification.service import NotificationService, RealWorldSMSProvider
from tests.fakes import FakeChannelProvider, FakeSMSProvider


def _task(**overrides) -> NotificationTask:
    defaults = {
        "tenant_id": "tenant-a",
        "team_id": "team-1",
        "trip_id": "trip-1",
        "customer_id": "13800138000",
        "rendered_content": "hello",
        "primary_channel": Channel.SMS,
        "fallback_channel": None,
        "idempotency_key": "notify:tenant-a:trip-1:morning:2026-11-05",
        "max_retry": 2,
    }
    defaults.update(overrides)
    return NotificationTask(**defaults)


def test_successful_dispatch_marks_idempotency_and_skips_duplicate() -> None:
    sms = FakeChannelProvider(default=(True, "ok"))
    store = IdempotencyStore()
    service = NotificationService(
        providers={Channel.SMS: sms},
        idempotency_store=store,
    )
    task = _task()

    first = service.dispatch(task)
    second = service.dispatch(task)

    assert first["ok"] is True
    assert second["reason"] == "idempotent_skip"
    assert task.status is DispatchStatus.SKIPPED
    assert sms.call_count == 1
    assert store.seen(task.idempotency_key)
    assert store.state(task.idempotency_key) == "sent"


def test_idempotency_store_reads_legacy_rows_without_status(json_store) -> None:
    json_store.write_collection("notification_idempotency", [{"key": "legacy-key"}])
    store = IdempotencyStore(store=json_store)

    assert store.seen("legacy-key")
    assert store.state("legacy-key") == "sent"


def test_failed_dispatch_does_not_mark_idempotency_key() -> None:
    sms = FakeChannelProvider(
        outcomes=[(False, "http_500"), (False, "http_500")],
        default=(True, "ok"),
    )
    store = IdempotencyStore()
    service = NotificationService(
        providers={Channel.SMS: sms},
        idempotency_store=store,
    )
    task = _task(max_retry=2)

    first = service.dispatch(task)
    assert first["ok"] is False
    assert not store.seen(task.idempotency_key)

    second = service.dispatch(task)
    assert second["ok"] is True
    assert sms.call_count == 3


def test_provider_exception_is_captured_as_failed_attempt() -> None:
    class RaisingProvider:
        def __init__(self) -> None:
            self.calls = 0

        def send(self, customer_id: str, content: str, provider_context=None):
            self.calls += 1
            raise RuntimeError("provider boom")

    provider = RaisingProvider()
    service = NotificationService(
        providers={Channel.SMS: provider},  # type: ignore[dict-item]
        idempotency_store=IdempotencyStore(),
    )
    task = _task(max_retry=1)

    result = service.dispatch(task)

    assert result["ok"] is False
    assert result["reason"] == "retry_exhausted"
    assert provider.calls == 1
    assert task.status is DispatchStatus.MANUAL_INTERVENTION
    assert len(task.attempts) == 1
    assert "provider_exception" in task.attempts[0].provider_message.lower()


def test_timeout_is_treated_as_unknown_and_not_retried() -> None:
    class TimeoutProvider:
        def __init__(self) -> None:
            self.calls = 0

        def send(self, customer_id: str, content: str, provider_context=None):
            self.calls += 1
            raise TimeoutError("read timed out")

    provider = TimeoutProvider()
    store = IdempotencyStore()
    service = NotificationService(
        providers={Channel.SMS: provider},  # type: ignore[dict-item]
        idempotency_store=store,
    )
    task = _task(max_retry=3)

    first = service.dispatch(task)
    second = service.dispatch(task)

    assert first["ok"] is False
    assert first["reason"] == "delivery_unknown"
    assert provider.calls == 1
    assert task.status is DispatchStatus.MANUAL_INTERVENTION
    assert store.state(task.idempotency_key) == "unknown"
    assert second["reason"] == "delivery_unknown_manual_review"
    assert provider.calls == 1


def test_provider_timeout_message_is_treated_as_unknown() -> None:
    provider = FakeChannelProvider(default=(False, "request_failed:timed out"))
    store = IdempotencyStore()
    service = NotificationService(
        providers={Channel.SMS: provider},
        idempotency_store=store,
    )
    task = _task(max_retry=3)

    result = service.dispatch(task)

    assert result["reason"] == "delivery_unknown"
    assert provider.call_count == 1
    assert store.state(task.idempotency_key) == "unknown"


def test_empty_content_is_not_retried() -> None:
    sms = FakeChannelProvider(default=(False, "empty_content"))
    service = NotificationService(
        providers={Channel.SMS: sms},
        idempotency_store=IdempotencyStore(),
    )
    task = _task(rendered_content="", max_retry=3)

    result = service.dispatch(task)

    assert result["ok"] is False
    assert sms.call_count == 1


def test_real_sms_provider_rejects_non_phone_customer_id() -> None:
    sms = FakeSMSProvider()
    adapter = RealWorldSMSProvider(sms)

    ok, message = adapter.send("system", "hello")

    assert ok is False
    assert message == "invalid_phone"
    assert sms.calls == []


def test_real_sms_provider_accepts_valid_phone() -> None:
    sms = FakeSMSProvider(default={"ok": True, "msg_id": "sms-1"})
    adapter = RealWorldSMSProvider(sms)

    ok, message = adapter.send("13800138000", "hello")

    assert ok is True
    assert message == "sms-1"
    assert sms.calls[0]["phone"] == "13800138000"


def test_mock_sms_provider_does_not_print_customer_data(capsys: pytest.CaptureFixture[str]) -> None:
    provider = MockSMSProvider()
    provider.send_sms("13800138000", "secret content")

    captured = capsys.readouterr()
    assert "13800138000" not in captured.out
    assert "secret content" not in captured.out


def test_primary_failure_falls_back_to_wechat() -> None:
    sms = FakeChannelProvider(default=(False, "http_500"))
    wechat = FakeChannelProvider(default=(True, "ok"))
    store = IdempotencyStore()
    service = NotificationService(
        providers={Channel.SMS: sms, Channel.WECHAT_WORK_GROUP: wechat},
        idempotency_store=store,
    )
    task = _task(primary_channel=Channel.SMS, fallback_channel=Channel.WECHAT_WORK_GROUP)

    result = service.dispatch(task)

    assert result["ok"] is True
    assert task.status is DispatchStatus.SENT
    assert sms.call_count == 2
    assert wechat.call_count == 1
    assert store.seen(task.idempotency_key)


def test_fallback_equal_to_primary_is_not_sent_twice() -> None:
    sms = FakeChannelProvider(default=(False, "http_500"))
    service = NotificationService(
        providers={Channel.SMS: sms},
        idempotency_store=IdempotencyStore(),
    )
    task = _task(primary_channel=Channel.SMS, fallback_channel=Channel.SMS)

    result = service.dispatch(task)

    assert result["ok"] is False
    assert sms.call_count == 2


def test_missing_provider_marks_manual_intervention() -> None:
    service = NotificationService(
        providers={Channel.SMS: FakeChannelProvider()},
        idempotency_store=IdempotencyStore(),
    )
    task = _task(primary_channel=Channel.WECHAT_WORK_GROUP, fallback_channel=None)

    result = service.dispatch(task)

    assert result["ok"] is False
    assert task.status is DispatchStatus.MANUAL_INTERVENTION


@pytest.mark.parametrize(
    "provider_message",
    ["wechat_webhook_not_configured", "sms_provider_not_configured", "invalid_webhook_url"],
)
def test_configuration_errors_are_not_retried(provider_message: str) -> None:
    sms = FakeChannelProvider(default=(False, provider_message))
    service = NotificationService(
        providers={Channel.SMS: sms},
        idempotency_store=IdempotencyStore(),
    )
    task = _task(max_retry=3)

    service.dispatch(task)

    assert sms.call_count == 1


def test_render_rejects_missing_variables() -> None:
    from app.modules.notification.models import NotificationTemplate

    service = NotificationService(
        providers={Channel.SMS: FakeChannelProvider()},
        idempotency_store=IdempotencyStore(),
    )
    template = NotificationTemplate(content="{{ customer_name }} / {{ destination }}")

    with pytest.raises(ValueError) as exc:
        service.render(template, {"customer_name": "张三"})

    assert "destination" in str(exc.value)


def test_render_supports_whitespace_and_repeated_placeholders() -> None:
    from app.modules.notification.models import NotificationTemplate

    service = NotificationService(
        providers={Channel.SMS: FakeChannelProvider()},
        idempotency_store=IdempotencyStore(),
    )
    template = NotificationTemplate(content="你好 {{ customer_name }}，{{customer_name}}")

    assert service.render(template, {"customer_name": "张三"}) == "你好 张三，张三"


def test_legacy_provider_without_context_is_supported() -> None:
    class LegacyProvider:
        def send(self, customer_id: str, content: str):
            return True, "legacy-ok"

    service = NotificationService(
        providers={Channel.SMS: LegacyProvider()},  # type: ignore[dict-item]
        idempotency_store=IdempotencyStore(),
    )

    result = service.dispatch(_task())

    assert result["ok"] is True


def test_real_sms_provider_forwards_template_metadata() -> None:
    sms = FakeSMSProvider()
    adapter = RealWorldSMSProvider(sms)

    ok, message = adapter.send(
        "13800138000",
        "hello",
        {
            "sms_sign_name": "TravelHub",
            "provider_template_code": "SMS_123",
            "template_params": {"name": "张三"},
        },
    )

    assert ok is True
    assert message == "fake-sms"
    assert sms.calls[0]["sign_name"] == "TravelHub"
    assert sms.calls[0]["template_code"] == "SMS_123"
    assert sms.calls[0]["template_params"] == {"name": "张三"}
