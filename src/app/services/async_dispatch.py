from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from app.modules.notification.models import NotificationTask
from app.modules.notification.service import NotificationService

UTC = timezone.utc


@dataclass(slots=True)
class NotificationJob:
    job_id: str
    task_id: str
    tenant_id: str
    team_id: str
    trip_id: str
    channel: str
    status: str
    attempt: int
    next_run_at: datetime
    created_at: datetime
    updated_at: datetime
    last_error: str = ""
    last_latency_ms: int = 0
    started_at: datetime | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "task_id": self.task_id,
            "tenant_id": self.tenant_id,
            "team_id": self.team_id,
            "trip_id": self.trip_id,
            "channel": self.channel,
            "status": self.status,
            "attempt": self.attempt,
            "next_run_at": self.next_run_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_error": self.last_error,
            "last_latency_ms": self.last_latency_ms,
            "started_at": self.started_at.isoformat() if self.started_at else None,
        }


@dataclass(slots=True)
class AsyncDispatchService:
    notification_service: NotificationService
    max_attempt: int = 3
    backoff_minutes: tuple[int, ...] = (1, 3, 9)
    _jobs: list[NotificationJob] = field(default_factory=list)

    def enqueue(self, task: NotificationTask, *, channel: str) -> NotificationJob:
        now = datetime.now(tz=UTC)
        job = NotificationJob(
            job_id=f"job-{uuid4().hex[:10]}",
            task_id=task.id,
            tenant_id=task.tenant_id,
            team_id=task.team_id,
            trip_id=task.trip_id,
            channel=channel,
            status="pending",
            attempt=0,
            next_run_at=now,
            created_at=now,
            updated_at=now,
        )
        self._jobs.insert(0, job)
        return job

    def list_jobs(
        self,
        *,
        tenant_id: str,
        team_id: str | None = None,
        trip_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        items = [item for item in self._jobs if item.tenant_id == tenant_id]
        if team_id:
            items = [item for item in items if item.team_id == team_id]
        if trip_id:
            items = [item for item in items if item.trip_id == trip_id]
        if status:
            items = [item for item in items if item.status == status]
        return [item.to_payload() for item in items[: max(0, limit)]]

    def run_due_jobs(self, tasks: dict[str, NotificationTask]) -> list[dict[str, Any]]:
        now = datetime.now(tz=UTC)
        processed: list[dict[str, Any]] = []
        for job in self._jobs:
            if job.status not in {"pending", "retrying"}:
                continue
            if job.next_run_at > now:
                continue
            task = tasks.get(job.task_id)
            if task is None:
                job.status = "failed"
                job.last_error = "task_not_found"
                job.updated_at = now
                processed.append(job.to_payload())
                continue
            job.started_at = now
            result = self.notification_service.dispatch(task)
            job.attempt += 1
            job.updated_at = datetime.now(tz=UTC)
            job.last_latency_ms = 0
            skipped_due_idempotency = result.get("reason") == "idempotent_skip"
            if result.get("ok") is True and not skipped_due_idempotency:
                job.status = "sent"
                job.last_error = ""
            elif job.attempt >= self.max_attempt:
                job.status = "manual_intervention"
                job.last_error = str(result.get("reason") or "retry_exhausted")
            else:
                job.status = "retrying"
                delay = self._backoff(job.attempt)
                job.next_run_at = datetime.now(tz=UTC) + timedelta(minutes=delay)
                job.last_error = str(result.get("reason") or "send_failed")
            processed.append(job.to_payload())
        return processed

    def health_snapshot(self) -> dict[str, Any]:
        now = datetime.now(tz=UTC)
        pending = [j for j in self._jobs if j.status in {"pending", "retrying"}]
        failures_5m = [
            j
            for j in self._jobs
            if j.status in {"failed", "manual_intervention"}
            and (now - j.updated_at) <= timedelta(minutes=5)
        ]
        oldest_age = 0
        if pending:
            oldest_pending = min(pending, key=lambda item: item.created_at)
            oldest_age = int((now - oldest_pending.created_at).total_seconds())
        return {
            "queue_backlog": len(pending),
            "oldest_pending_job_age": oldest_age,
            "error_burst_5m": len(failures_5m),
        }

    def _backoff(self, attempt: int) -> int:
        index = min(max(attempt - 1, 0), len(self.backoff_minutes) - 1)
        return self.backoff_minutes[index]
