from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from threading import RLock
from typing import Any
from uuid import uuid4

from app.modules.integration.persistence import JsonFileStore
from app.modules.notification.models import NotificationTask
from app.modules.notification.service import NotificationService

UTC = UTC


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
    store: JsonFileStore | None = None
    collection: str = "notification_jobs"
    _jobs: list[NotificationJob] = field(default_factory=list)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.store is None:
            return
        for row in self.store.read_collection(self.collection):
            try:
                self._jobs.append(
                    NotificationJob(
                        job_id=str(row["job_id"]),
                        task_id=str(row["task_id"]),
                        tenant_id=str(row.get("tenant_id", "")),
                        team_id=str(row.get("team_id", "")),
                        trip_id=str(row.get("trip_id", "")),
                        channel=str(row.get("channel", "sms")),
                        status=str(row.get("status", "pending")),
                        attempt=int(row.get("attempt", 0)),
                        next_run_at=datetime.fromisoformat(str(row["next_run_at"])),
                        created_at=datetime.fromisoformat(str(row["created_at"])),
                        updated_at=datetime.fromisoformat(str(row["updated_at"])),
                        last_error=str(row.get("last_error", "")),
                        last_latency_ms=int(row.get("last_latency_ms", 0)),
                        started_at=(
                            datetime.fromisoformat(str(row["started_at"]))
                            if row.get("started_at")
                            else None
                        ),
                    )
                )
            except (KeyError, TypeError, ValueError):
                # Ignore malformed rows instead of losing the whole queue.
                continue

    def _persist(self) -> None:
        if self.store is None:
            return
        self.store.write_collection(
            self.collection, [job.to_payload() for job in self._jobs]
        )

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
        with self._lock:
            self._jobs.insert(0, job)
            self._persist()
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
        with self._lock:
            items = [item for item in self._jobs if item.tenant_id == tenant_id]
            if team_id:
                items = [item for item in items if item.team_id == team_id]
            if trip_id:
                items = [item for item in items if item.trip_id == trip_id]
            if status:
                items = [item for item in items if item.status == status]
            return [item.to_payload() for item in items[: max(0, limit)]]

    def requeue(self, job_id: str, *, tenant_id: str) -> dict[str, Any] | None:
        """Requeue a dead-letter/failed job for a fresh attempt budget."""
        with self._lock:
            job = next((item for item in self._jobs if item.job_id == job_id), None)
            if job is None or job.tenant_id != tenant_id:
                return None
            if job.status not in {"manual_intervention", "failed", "retrying"}:
                return None
            now = datetime.now(tz=UTC)
            job.status = "pending"
            job.attempt = 0
            job.next_run_at = now
            job.last_error = ""
            job.started_at = None
            job.updated_at = now
            self._persist()
            return job.to_payload()

    def run_due_jobs(self, tasks: dict[str, NotificationTask]) -> list[dict[str, Any]]:
        lock_store = self.store
        if lock_store is not None:
            if not lock_store.acquire_advisory_lock("notification_jobs"):
                # Another process/worker owns the queue; skip this tick.
                return []
        try:
            return self._run_due_jobs_locked(tasks)
        finally:
            if lock_store is not None:
                lock_store.release_advisory_lock("notification_jobs")

    def _run_due_jobs_locked(
        self, tasks: dict[str, NotificationTask]
    ) -> list[dict[str, Any]]:
        now = datetime.now(tz=UTC)
        processed: list[dict[str, Any]] = []
        with self._lock:
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
                # Claim the job before calling the provider so concurrent workers
                # in this process cannot send the same job twice.
                job.status = "processing"
                job.updated_at = now
                self._persist()
                job.started_at = now
                try:
                    result = self.notification_service.dispatch(task)
                except Exception as exc:  # noqa: BLE001 - outbox must not crash
                    result = {
                        "ok": False,
                        "reason": f"dispatch_exception:{type(exc).__name__}:{exc}",
                    }
                job.attempt += 1
                job.updated_at = datetime.now(tz=UTC)
                job.last_latency_ms = _last_latency(task)
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
            self._persist()
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


def _last_latency(task: NotificationTask) -> int:
    if not task.attempts:
        return 0
    return int(task.attempts[-1].latency_ms)
