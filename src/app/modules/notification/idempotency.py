from __future__ import annotations

from dataclasses import dataclass, field

from app.modules.integration.persistence import JsonFileStore


@dataclass(slots=True)
class IdempotencyStore:
    """Idempotency storage with optional shared persistence backend.

    States:
    - ``sent``: provider accepted the message; never send again.
    - ``unknown``: a timeout/ambiguous failure occurred. Do not auto-retry
      (the provider may have accepted it); route to manual review instead.
    - missing: retryable failure or never attempted.
    """

    store: JsonFileStore | None = None
    collection: str = "notification_idempotency"
    seen_keys: set[str] = field(default_factory=set)
    states: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.store is None:
            return
        rows = self.store.read_collection(self.collection)
        for row in rows:
            key = str(row.get("key", "")).strip()
            if not key:
                continue
            status = str(row.get("status", "sent") or "sent").strip().lower()
            self.states[key] = status
            if status == "sent":
                self.seen_keys.add(key)

    def _flush(self) -> None:
        if self.store is None:
            return
        payload = [
            {"key": key, "status": self.states.get(key, "sent")}
            for key in sorted(self.states)
        ]
        self.store.write_collection(self.collection, payload)

    def seen(self, key: str) -> bool:
        """Return True only when the key was successfully sent."""
        return key in self.seen_keys or self.states.get(key) == "sent"

    def state(self, key: str) -> str:
        if key in self.states:
            return self.states[key]
        return "sent" if key in self.seen_keys else ""

    def terminal(self, key: str) -> bool:
        return self.state(key) in {"sent", "unknown"}

    def mark(self, key: str, status: str = "sent") -> None:
        if not key:
            return
        normalized = status.strip().lower() or "sent"
        self.states[key] = normalized
        if normalized == "sent":
            self.seen_keys.add(key)
        self._flush()
