from __future__ import annotations

from app.core.models import Channel
from app.modules.notification.models import NotificationTask
from app.modules.notification.service import NotificationService


class FailSmsProvider:
    def send(self, customer_id: str, content: str) -> tuple[bool, str]:
        return False, "sms_down"


class OkGroupProvider:
    def send(self, customer_id: str, content: str) -> tuple[bool, str]:
        return True, "group_ok"


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
