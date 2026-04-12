from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from time import monotonic
from typing import Any, Protocol

from app.core.models import Channel
from app.modules.integration.persistence import JsonFileStore
from app.modules.notification.idempotency import IdempotencyStore
from app.modules.notification.models import (
    DispatchStatus,
    NotificationAttempt,
    NotificationTask,
    NotificationTemplate,
)

UTC = UTC


class ChannelProvider(Protocol):
    def send(self, customer_id: str, content: str) -> tuple[bool, str]:
        """Return (ok, provider_message)."""


class StubProvider:
    """Default provider used in MVP demo/tests."""

    def send(self, customer_id: str, content: str) -> tuple[bool, str]:
        if not content.strip():
            return False, "empty_content"
        return True, f"accepted:{customer_id}"


@dataclass(slots=True)
class NotificationAttemptRepository:
    store: JsonFileStore | None = None
    collection: str = "notification_attempts"
    _records: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.store is None:
            return
        self._records = self.store.read_collection(self.collection)

    def _to_value(self, value: Any) -> Any:
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    def record_attempt(
        self, task: NotificationTask, attempt: NotificationAttempt
    ) -> dict[str, Any]:
        latest_attempt_no = max(
            (
                int(item.get("attempt_no", 0))
                for item in self._records
                if str(item.get("task_id", "")) == task.id
            ),
            default=0,
        )
        persisted_attempt_no = latest_attempt_no + 1
        payload = {
            "attempt_id": attempt.id,
            "task_id": task.id,
            "tenant_id": task.tenant_id,
            "trip_id": task.trip_id,
            "team_id": task.team_id,
            "customer_id": task.customer_id,
            "attempt_no": persisted_attempt_no,
            "channel": attempt.channel.value,
            "ok": attempt.ok,
            "reason": attempt.reason,
            "provider_message": attempt.provider_message,
            "latency_ms": attempt.latency_ms,
            "status": task.status.value,
            "attempted_at": attempt.attempted_at.isoformat(),
        }
        self._records.insert(0, payload)
        if self.store is not None:
            self.store.write_collection(self.collection, self._records)
        return payload

    def list_history(
        self,
        *,
        limit: int | None = 20,
        trip_id: str | None = None,
        team_id: str | None = None,
        customer_id: str | None = None,
    ) -> list[dict[str, Any]]:
        items = self._records
        if trip_id:
            items = [item for item in items if item.get("trip_id") == trip_id]
        if team_id:
            items = [item for item in items if item.get("team_id") == team_id]
        if customer_id:
            items = [item for item in items if item.get("customer_id") == customer_id]
        if limit is None:
            return items
        return items[: max(limit, 0)]


class NotificationService:
    """通知模块服务：模板渲染 + 重试 + 兜底 + 幂等。"""

    def __init__(
        self,
        providers: dict[Channel, ChannelProvider] | None = None,
        idempotency_store: IdempotencyStore | None = None,
        attempt_repository: NotificationAttemptRepository | None = None,
    ) -> None:
        default_provider = StubProvider()
        self.providers: dict[Channel, ChannelProvider] = providers or {
            Channel.SMS: default_provider,
            Channel.WECHAT_WORK_GROUP: default_provider,
        }
        self.idempotency_store = idempotency_store or IdempotencyStore()
        self.attempt_repository = attempt_repository

    def render(self, template: NotificationTemplate, variables: dict[str, str]) -> str:
        content = template.content
        for key, value in variables.items():
            content = content.replace("{{" + key + "}}", value)
        return content

    def dispatch(self, task: NotificationTask) -> dict:
        if task.idempotency_key and self.idempotency_store.seen(task.idempotency_key):
            task.status = DispatchStatus.SKIPPED
            return {"ok": True, "reason": "idempotent_skip", "task": asdict(task)}

        channels = [task.primary_channel]
        if task.fallback_channel and task.fallback_channel != task.primary_channel:
            channels.append(task.fallback_channel)

        for channel in channels:
            provider = self.providers.get(channel)
            if provider is None:
                continue

            for attempt in range(1, task.max_retry + 1):
                start = monotonic()
                ok, provider_message = provider.send(task.customer_id, task.rendered_content)
                latency_ms = int((monotonic() - start) * 1000)
                task.retry_count += 1
                task.attempts.append(
                    NotificationAttempt(
                        task_id=task.id,
                        attempt_no=attempt,
                        channel=channel,
                        ok=ok,
                        provider_message=provider_message,
                        reason="ok" if ok else "send_failed",
                        latency_ms=latency_ms,
                    )
                )
                if self.attempt_repository is not None:
                    self.attempt_repository.record_attempt(task, task.attempts[-1])
                if ok:
                    task.status = DispatchStatus.SENT
                    self.idempotency_store.mark(task.idempotency_key)
                    return {"ok": True, "task": asdict(task)}

        task.manual_intervention_required = True
        task.status = DispatchStatus.MANUAL_INTERVENTION
        self.idempotency_store.mark(task.idempotency_key)
        return {"ok": False, "reason": "retry_exhausted", "task": asdict(task)}
