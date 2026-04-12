from __future__ import annotations

from app.core.models import Channel
from app.modules.integration.rbac import PermissionDenied, assert_tenant_scope, require_permission
from app.modules.notification.models import NotificationTask
from app.modules.notification.service import NotificationService
from app.services.async_dispatch import AsyncDispatchService


class AlwaysFailProvider:
    def send(self, customer_id: str, content: str) -> tuple[bool, str]:
        return False, "network_down"


def test_require_permission_and_tenant_scope() -> None:
    user = {"role": "user", "tenant_id": "tenant-a"}
    require_permission(user, "trip:write")
    assert_tenant_scope(user, "tenant-a")

    try:
        assert_tenant_scope(user, "tenant-b")
    except PermissionDenied as exc:
        assert exc.code == "cross_tenant_forbidden"
    else:
        raise AssertionError("expected cross tenant denial")


def test_async_dispatch_retries_and_moves_to_manual_intervention() -> None:
    service = NotificationService(
        providers={
            Channel.SMS: AlwaysFailProvider(),
            Channel.WECHAT_WORK_GROUP: AlwaysFailProvider(),
        }
    )
    async_service = AsyncDispatchService(notification_service=service, max_attempt=2)
    task = NotificationTask(
        tenant_id="tenant-a",
        team_id="TEAM-01",
        trip_id="trip-001",
        customer_id="user-001",
        rendered_content="hello",
        idempotency_key="job:test:1",
        primary_channel=Channel.SMS,
        fallback_channel=Channel.WECHAT_WORK_GROUP,
    )

    job = async_service.enqueue(task, channel="sms")
    tasks = {task.id: task}

    first_round = async_service.run_due_jobs(tasks)
    assert len(first_round) == 1
    assert first_round[0]["status"] == "retrying"
    assert first_round[0]["attempt"] == 1

    # force second round due now
    async_service._jobs[0].next_run_at = async_service._jobs[0].created_at
    second_round = async_service.run_due_jobs(tasks)
    assert second_round[0]["job_id"] == job.job_id
    assert second_round[0]["status"] == "manual_intervention"
    assert second_round[0]["attempt"] == 2
