from __future__ import annotations

from app.core.models import Channel
from app.modules.integration.persistence import JsonFileStore
from app.modules.notification.models import NotificationTask
from app.modules.notification.service import NotificationAttemptRepository, NotificationService


class FailSmsProvider:
    def send(self, customer_id: str, content: str) -> tuple[bool, str]:
        return False, "sms_down"


class OkGroupProvider:
    def send(self, customer_id: str, content: str) -> tuple[bool, str]:
        return True, "group_ok"


class InvalidSmsProvider:
    def send(self, customer_id: str, content: str) -> tuple[bool, str]:
        return False, "invalid_phone"


def test_dispatch_fallback_to_wechat_group_when_sms_failed() -> None:
    service = NotificationService(
        providers={
            Channel.SMS: FailSmsProvider(),
            Channel.WECHAT_WORK_GROUP: OkGroupProvider(),
        }
    )
    task = NotificationTask(
        team_id="TEAM-1",
        customer_id="C-1",
        rendered_content="hello",
        max_retry=2,
    )

    result = service.dispatch(task)

    assert result["ok"] is True
    assert task.status.value == "sent"
    assert len(task.attempts) == 3
    assert task.attempts[-1].channel == Channel.WECHAT_WORK_GROUP


def test_dispatch_skips_retry_for_non_retryable_error_and_uses_fallback() -> None:
    service = NotificationService(
        providers={
            Channel.SMS: InvalidSmsProvider(),
            Channel.WECHAT_WORK_GROUP: OkGroupProvider(),
        }
    )
    task = NotificationTask(
        team_id="TEAM-2",
        customer_id="C-2",
        rendered_content="hello",
        max_retry=3,
    )

    result = service.dispatch(task)

    assert result["ok"] is True
    assert len(task.attempts) == 2
    assert task.attempts[0].provider_message == "invalid_phone"
    assert task.attempts[1].channel == Channel.WECHAT_WORK_GROUP


def test_dispatch_is_idempotent_with_same_key() -> None:
    service = NotificationService()
    task = NotificationTask(
        team_id="TEAM-1",
        customer_id="C-1",
        rendered_content="hello",
        idempotency_key="TEAM-1:daily:2026-01-01T08:00:00Z",
    )

    first = service.dispatch(task)
    second = service.dispatch(task)

    assert first["ok"] is True
    assert second["ok"] is True
    assert second["reason"] == "idempotent_skip"


def test_notification_attempts_are_persisted_for_history_query(tmp_path) -> None:
    store = JsonFileStore(base_dir=tmp_path)
    attempt_repository = NotificationAttemptRepository(store=store)
    service = NotificationService(attempt_repository=attempt_repository)
    task = NotificationTask(
        team_id="TEAM-99",
        trip_id="trip-99",
        customer_id="user-99",
        rendered_content="hello history",
    )

    result = service.dispatch(task)

    assert result["ok"] is True
    reloaded_repo = NotificationAttemptRepository(store=store)
    items = reloaded_repo.list_history(limit=10, trip_id="trip-99")
    assert len(items) >= 1
    assert items[0]["trip_id"] == "trip-99"
