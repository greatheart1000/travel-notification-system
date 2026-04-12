from __future__ import annotations

from dataclasses import dataclass, field

from app.modules.integration.persistence import JsonFileStore


@dataclass(slots=True)
class IdempotencyStore:
    """Idempotency storage with optional shared persistence backend."""

    store: JsonFileStore | None = None
    collection: str = "notification_idempotency"
    seen_keys: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        if self.store is None:
            return
        rows = self.store.read_collection(self.collection)
        self.seen_keys = {
            str(row.get("key", "")).strip() for row in rows if str(row.get("key", "")).strip()
        }

    def _flush(self) -> None:
        if self.store is None:
            return
        payload = [{"key": key} for key in sorted(self.seen_keys)]
        self.store.write_collection(self.collection, payload)

    def seen(self, key: str) -> bool:
        return key in self.seen_keys

    def mark(self, key: str) -> None:
        if key and key not in self.seen_keys:
            self.seen_keys.add(key)
            self._flush()
