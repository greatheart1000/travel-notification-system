from __future__ import annotations

from dataclasses import asdict
from time import monotonic
from typing import Protocol

from app.core.models import Channel
from app.modules.notification.idempotency import IdempotencyStore
from app.modules.notification.models import (
    DispatchStatus,
    NotificationAttempt,
    NotificationTask,
    NotificationTemplate,
)


class ChannelProvider(Protocol):
    def send(self, customer_id: str, content: str) -> tuple[bool, str]:
        """Return (ok, provider_message)."""


class StubProvider:
    """Default provider used in MVP demo/tests."""

    def send(self, customer_id: str, content: str) -> tuple[bool, str]:
        if not content.strip():
            return False, "empty_content"
        return True, f"accepted:{customer_id}"


class NotificationService:
    """通知模块服务：模板渲染 + 重试 + 兜底 + 幂等。"""

    def __init__(
        self,
        providers: dict[Channel, ChannelProvider] | None = None,
        idempotency_store: IdempotencyStore | None = None,
    ) -> None:
        default_provider = StubProvider()
        self.providers: dict[Channel, ChannelProvider] = providers or {
            Channel.SMS: default_provider,
            Channel.WECHAT_WORK_GROUP: default_provider,
        }
        self.idempotency_store = idempotency_store or IdempotencyStore()

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
                if ok:
                    task.status = DispatchStatus.SENT
                    self.idempotency_store.mark(task.idempotency_key)
                    return {"ok": True, "task": asdict(task)}

        task.manual_intervention_required = True
        task.status = DispatchStatus.MANUAL_INTERVENTION
        self.idempotency_store.mark(task.idempotency_key)
        return {"ok": False, "reason": "retry_exhausted", "task": asdict(task)}
