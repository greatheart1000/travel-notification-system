from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass

from app.core.entities import DomainEvent

EventHandler = Callable[[DomainEvent], None]


@dataclass(slots=True)
class OutboxMessage:
    event: DomainEvent
    published: bool = False


class InMemoryEventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self.outbox: list[OutboxMessage] = []

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        self._handlers[event_name].append(handler)

    def push_outbox(self, event: DomainEvent) -> None:
        self.outbox.append(OutboxMessage(event=event))

    def flush_outbox(self) -> int:
        published = 0
        for message in self.outbox:
            if message.published:
                continue
            for handler in self._handlers.get(message.event.name.value, []):
                handler(message.event)
            message.published = True
            published += 1
        return published
