from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from app.core.entities import Channel, DomainEvent, EventName


@dataclass(slots=True)
class Rule:
    event_name: EventName
    priority: int
    channels: list[Channel]
    max_per_hour: int = 2
    enabled: bool = True


@dataclass(slots=True)
class NotificationRuleEngine:
    rules: list[Rule] = field(default_factory=list)
    sent_counter: dict[str, list[datetime]] = field(default_factory=dict)

    def upsert_rule(self, rule: Rule) -> None:
        self.rules = [r for r in self.rules if r.event_name != rule.event_name] + [rule]

    def match(self, event: DomainEvent) -> Rule:
        candidates = [r for r in self.rules if r.event_name == event.name and r.enabled]
        if not candidates:
            raise ValueError(f"rule missing for {event.name}")
        return sorted(candidates, key=lambda x: x.priority)[0]

    def allow_send(self, user_id: str, event_name: EventName, now: datetime) -> bool:
        key = f"{user_id}:{event_name.value}"
        window_start = now - timedelta(hours=1)
        points = [t for t in self.sent_counter.get(key, []) if t >= window_start]
        self.sent_counter[key] = points
        max_per_hour = 2
        event_rules = [r for r in self.rules if r.event_name == event_name and r.enabled]
        if event_rules:
            max_per_hour = event_rules[0].max_per_hour
        if len(points) >= max_per_hour:
            return False
        self.sent_counter[key].append(now.astimezone(UTC))
        return True
