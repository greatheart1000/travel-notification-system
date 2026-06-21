from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from time import monotonic
from typing import Any, Protocol

from app.core.models import Channel
from app.modules.integration.persistence import JsonFileStore
from app.modules.integration.sms_provider import SMSProvider, get_sms_provider
from app.modules.integration.wechat_provider import WeChatWorkWebhookProvider
from app.modules.notification.idempotency import IdempotencyStore
from app.modules.notification.models import (
    DispatchStatus,
    NotificationAttempt,
    NotificationTask,
    NotificationTemplate,
)

UTC = UTC


class ChannelProvider(Protocol):
    def send(
        self,
        customer_id: str,
        content: str,
        provider_context: dict[str, str] | None = None,
    ) -> tuple[bool, str]:
        """Return (ok, provider_message)."""


class RealWorldSMSProvider:
    """适配 SMSProvider 接口到 NotificationService 的 ChannelProvider 协议。"""

    def __init__(self, provider: SMSProvider):
        self.provider = provider

    def send(
        self,
        customer_id: str,
        content: str,
        provider_context: dict[str, str] | None = None,
    ) -> tuple[bool, str]:
        # 假设 customer_id 就是手机号，实际场景需要从 Repository 查询
        phone = customer_id if customer_id.isdigit() else "13800000000"
        metadata = provider_context or {}
        result = self.provider.send_sms(
            phone,
            content,
            sign_name=metadata.get("sms_sign_name", "TravelHub"),
            template_code=metadata.get("provider_template_code", ""),
            template_params=metadata.get("template_params"),
        )
        return result["ok"], result.get("msg_id", result.get("error", "unknown"))


class StubProvider:
    """Default provider used in MVP demo/tests."""

    def send(
        self,
        customer_id: str,
        content: str,
        provider_context: dict[str, str] | None = None,
    ) -> tuple[bool, str]:
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
            "trip_label": task.provider_context.get("trip_label", task.trip_id),
            "team_id": task.team_id,
            "customer_id": task.customer_id,
            "customer_name": task.provider_context.get("customer_name", task.customer_id),
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

    def get_recent_items(self, *, tenant_id: str, limit: int) -> list[dict[str, Any]]:
        """Return recent notification items for the workbench feed."""
        from datetime import UTC, datetime

        items = [item for item in self._records if item.get("tenant_id") == tenant_id]
        items.sort(
            key=lambda item: (
                str(item.get("attempted_at") or datetime.now(tz=UTC).isoformat()),
                str(item.get("attempt_id") or ""),
            ),
            reverse=True,
        )
        recent: list[dict[str, Any]] = []
        for item in items[: max(limit, 0)]:
            recent.append(
                {
                    "id": str(item.get("attempt_id") or ""),
                    "customer_name": str(item.get("customer_name") or item.get("customer_id") or ""),
                    "trip": str(item.get("trip_label") or item.get("trip_id") or ""),
                    "channel": str(item.get("channel") or "sms"),
                    "status": str(item.get("status") or ("sent" if item.get("ok") else "failed")),
                    "created_at": str(item.get("attempted_at") or ""),
                }
            )
        return recent


class NotificationService:
    """通知模块服务：模板渲染 + 重试 + 兜底 + 幂等。"""

    def __init__(
        self,
        providers: dict[Channel, ChannelProvider] | None = None,
        idempotency_store: IdempotencyStore | None = None,
        attempt_repository: NotificationAttemptRepository | None = None,
    ) -> None:
        sms_backend = RealWorldSMSProvider(get_sms_provider())
        self.providers: dict[Channel, ChannelProvider] = providers or {
            Channel.SMS: sms_backend,
            Channel.WECHAT_WORK_GROUP: WeChatWorkWebhookProvider(),
        }
        self.idempotency_store = idempotency_store or IdempotencyStore()
        self.attempt_repository = attempt_repository

    def render(self, template: NotificationTemplate, variables: dict[str, str]) -> str:
        placeholders = set(re.findall(r"{{\s*([a-zA-Z0-9_]+)\s*}}", template.content))
        missing_fields = [name for name in sorted(placeholders) if name not in variables]
        if missing_fields:
            raise ValueError(f"missing_template_variables:{','.join(missing_fields)}")
        content = template.content
        for key, value in variables.items():
            content = content.replace("{{" + key + "}}", value)
        return content

    def _is_retryable_error(self, provider_message: str) -> bool:
        raw = provider_message.strip().lower()
        non_retryable_prefixes = (
            "invalid_",
            "forbidden_",
            "unauthorized_",
            "missing_",
            "bad_request",
        )
        if raw.startswith(non_retryable_prefixes):
            return False
        if "permanent" in raw:
            return False
        return True

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
                try:
                    ok, provider_message = provider.send(
                        task.customer_id,
                        task.rendered_content,
                        task.provider_context,
                    )
                except TypeError:
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
                if not self._is_retryable_error(provider_message):
                    break

        task.manual_intervention_required = True
        task.status = DispatchStatus.MANUAL_INTERVENTION
        self.idempotency_store.mark(task.idempotency_key)
        return {"ok": False, "reason": "retry_exhausted", "task": asdict(task)}
