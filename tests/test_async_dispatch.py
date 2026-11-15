from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.core.models import Channel
from app.modules.notification.models import NotificationTask
from app.modules.notification.service import NotificationService
from app.services.async_dispatch import AsyncDispatchService
from tests.fakes import FakeChannelProvider


def _task() -> NotificationTask:
    return NotificationTask(
        tenant_id="tenant-a",
        team_id="team-1",
        trip_id="trip-1",
        customer_id="13800138000",
        rendered_content="hello",
        primary_channel=Channel.SMS,
        fallback_channel=None,
        idempotency_key="async:tenant-a:trip-1:1",
        max_retry=1,
    )


def _service(provider: FakeChannelProvider, **kwargs) -> NotificationService:
    return NotificationService(
        providers={Channel.SMS: provider},
        **kwargs,
    )


def test_queued_job_is_dispatched_when_due() -> None:
    provider = FakeChannelProvider(default=(True, "ok"))
    notification_service = _service(provider)
    queue = AsyncDispatchService(notification_service=notification_service)
    task = _task()

    job = queue.enqueue(task, channel="sms")
    processed = queue.run_due_jobs({task.id: task})

    assert job.status == "sent"
    assert task.status.value == "sent"
    assert provider.call_count == 1
    assert processed[0]["job_id"] == job.job_id


def test_failed_job_is_rescheduled_with_backoff() -> None:
    provider = FakeChannelProvider(default=(False, "http_500"))
    queue = AsyncDispatchService(
        notification_service=_service(provider),
        max_attempt=2,
        backoff_minutes=(1, 3),
    )
    task = _task()
    job = queue.enqueue(task, channel="sms")

    queue.run_due_jobs({task.id: task})

    assert job.status == "retrying"
    assert job.attempt == 1
    assert job.next_run_at > datetime.now(tz=UTC)
    assert job.last_error


def test_job_reaches_dead_letter_after_max_attempts() -> None:
    provider = FakeChannelProvider(default=(False, "http_500"))
    queue = AsyncDispatchService(
        notification_service=_service(provider),
        max_attempt=2,
        backoff_minutes=(1,),
    )
    task = _task()
    job = queue.enqueue(task, channel="sms")

    queue.run_due_jobs({task.id: task})
    job.next_run_at = datetime.now(tz=UTC) - timedelta(seconds=1)
    processed = queue.run_due_jobs({task.id: task})

    assert job.status == "manual_intervention"
    assert job.attempt == 2
    assert processed[-1]["status"] == "manual_intervention"


def test_missing_task_fails_job_without_crashing() -> None:
    queue = AsyncDispatchService(
        notification_service=_service(FakeChannelProvider()),
    )
    task = _task()
    job = queue.enqueue(task, channel="sms")

    processed = queue.run_due_jobs({})

    assert job.status == "failed"
    assert job.last_error == "task_not_found"
    assert processed[0]["job_id"] == job.job_id


def test_jobs_are_persisted_and_reloaded(json_store) -> None:
    provider = FakeChannelProvider(default=(True, "ok"))
    queue = AsyncDispatchService(
        notification_service=_service(provider),
        store=json_store,
    )
    task = _task()
    job = queue.enqueue(task, channel="sms")

    reloaded = AsyncDispatchService(
        notification_service=_service(provider),
        store=json_store,
    )
    jobs = reloaded.list_jobs(tenant_id="tenant-a")

    assert [item["job_id"] for item in jobs] == [job.job_id]
    assert jobs[0]["status"] == "pending"


def test_due_job_is_only_processed_once_per_run() -> None:
    provider = FakeChannelProvider(default=(True, "ok"))
    queue = AsyncDispatchService(notification_service=_service(provider))
    task = _task()
    queue.enqueue(task, channel="sms")

    queue.run_due_jobs({task.id: task})
    queue.run_due_jobs({task.id: task})

    assert provider.call_count == 1


def test_dispatch_exception_does_not_leave_job_stuck_in_processing() -> None:
    class RaisingNotificationService:
        def dispatch(self, task):  # noqa: ANN001
            raise RuntimeError("boom")

    queue = AsyncDispatchService(
        notification_service=RaisingNotificationService(),  # type: ignore[arg-type]
        max_attempt=1,
    )
    task = _task()
    job = queue.enqueue(task, channel="sms")

    processed = queue.run_due_jobs({task.id: task})

    assert job.status == "manual_intervention"
    assert "dispatch_exception" in job.last_error
    assert processed[-1]["status"] == "manual_intervention"


def test_due_jobs_are_skipped_when_another_worker_holds_the_lock(json_store) -> None:
    provider = FakeChannelProvider(default=(True, "ok"))
    queue = AsyncDispatchService(
        notification_service=_service(provider),
        store=json_store,
    )
    task = _task()
    queue.enqueue(task, channel="sms")

    assert json_store.acquire_advisory_lock("notification_jobs")
    try:
        processed = queue.run_due_jobs({task.id: task})
    finally:
        json_store.release_advisory_lock("notification_jobs")

    assert processed == []
    assert provider.call_count == 0

    queue.run_due_jobs({task.id: task})
    assert provider.call_count == 1


def test_dead_letter_job_can_be_requeued(json_store) -> None:
    provider = FakeChannelProvider(
        outcomes=[(False, "http_500")],
        default=(True, "ok"),
    )
    queue = AsyncDispatchService(
        notification_service=_service(provider),
        store=json_store,
        max_attempt=1,
    )
    task = _task()
    job = queue.enqueue(task, channel="sms")
    queue.run_due_jobs({task.id: task})
    assert job.status == "manual_intervention"

    requeued = queue.requeue(job.job_id, tenant_id="tenant-a")

    assert requeued is not None
    assert requeued["status"] == "pending"
    assert requeued["last_error"] == ""
    queue.run_due_jobs({task.id: task})
    assert job.status == "sent"


def test_requeue_rejects_cross_tenant_job(json_store) -> None:
    queue = AsyncDispatchService(
        notification_service=_service(FakeChannelProvider()),
        store=json_store,
    )
    task = _task()
    job = queue.enqueue(task, channel="sms")

    assert queue.requeue(job.job_id, tenant_id="tenant-b") is None
