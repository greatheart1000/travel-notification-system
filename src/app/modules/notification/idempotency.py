from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class IdempotencyStore:
    """Simple in-memory idempotency storage for MVP."""

    seen_keys: set[str] = field(default_factory=set)

    def seen(self, key: str) -> bool:
        return key in self.seen_keys

    def mark(self, key: str) -> None:
        if key:
            self.seen_keys.add(key)
