from __future__ import annotations

from dataclasses import dataclass, field

from app.core.entities import Channel, DeliveryStatus, DomainEvent, NotificationRecord
from app.providers.adapters import BaseProvider, ProviderResult


@dataclass(slots=True)
class DispatchService:
    providers: dict[Channel, BaseProvider]
    records: list[NotificationRecord] = field(default_factory=list)
    seen_dedupe: set[str] = field(default_factory=set)
    seen_event: set[str] = field(default_factory=set)

    def _dedupe_key(self, event: DomainEvent, channel: Channel) -> str:
        return f"{event.event_id}:{event.user_id}:{channel.value}"

    def send_with_fallback(
        self,
        event: DomainEvent,
        content: str,
        channels: list[Channel],
        max_retry: int = 1,
    ) -> NotificationRecord:
        if event.event_id in self.seen_event:
            return NotificationRecord(
                event_id=event.event_id,
                user_id=event.user_id,
                trip_id=event.trip_id,
                channel=channels[0],
                status=DeliveryStatus.SKIPPED,
                provider_response="idempotent skip",
            )

        last_record: NotificationRecord | None = None
        for channel in channels:
            dedupe_key = self._dedupe_key(event, channel)
            if dedupe_key in self.seen_dedupe:
                continue

            for attempt in range(1, max_retry + 1):
                result = self.providers[channel].send(event.user_id, content)
                status = DeliveryStatus.SUCCESS if result.ok else DeliveryStatus.RETRYING
                record = NotificationRecord(
                    event_id=event.event_id,
                    user_id=event.user_id,
                    trip_id=event.trip_id,
                    channel=channel,
                    status=status,
                    attempt=attempt,
                    dedupe_key=dedupe_key,
                    provider_response=result.message,
                )
                self.records.append(record)
                last_record = record
                if result.ok:
                    self.seen_dedupe.add(dedupe_key)
                    self.seen_event.add(event.event_id)
                    return record

            fail_record = NotificationRecord(
                event_id=event.event_id,
                user_id=event.user_id,
                trip_id=event.trip_id,
                channel=channel,
                status=DeliveryStatus.FAILED,
                attempt=max_retry,
                dedupe_key=dedupe_key,
                provider_response="retry exhausted",
            )
            self.records.append(fail_record)
            last_record = fail_record

        if last_record is None:
            raise RuntimeError("dispatch failed without records")
        return last_record
