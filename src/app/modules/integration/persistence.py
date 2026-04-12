from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from threading import RLock
from typing import Any

DEFAULT_DB_DIR = "/tmp/travel-notification-system"


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    return str(value)


@dataclass(slots=True)
class JsonFileStore:
    """Minimal JSON file storage for MVP persistence."""

    base_dir: str | Path | None = None
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.base_dir is None:
            self.base_dir = os.getenv("TRAVEL_NOTIFICATION_DB_DIR", DEFAULT_DB_DIR)
        self.base_dir = Path(self.base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _collection_path(self, collection: str) -> Path:
        return Path(self.base_dir) / f"{collection}.json"

    def read_collection(self, collection: str) -> list[dict[str, Any]]:
        path = self._collection_path(collection)
        if not path.exists():
            return []
        with self._lock:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return []
        if not isinstance(data, list):
            return []
        return [item for item in data if isinstance(item, dict)]

    def write_collection(self, collection: str, items: list[dict[str, Any]]) -> None:
        path = self._collection_path(collection)
        payload = json.dumps(items, ensure_ascii=False, default=_json_default, indent=2)
        temp_path = path.with_suffix(".tmp")
        with self._lock:
            temp_path.write_text(payload, encoding="utf-8")
            temp_path.replace(path)

    def upsert(self, collection: str, item: dict[str, Any], key: str = "id") -> dict[str, Any]:
        items = self.read_collection(collection)
        existing_index = next(
            (idx for idx, row in enumerate(items) if row.get(key) == item.get(key)), None
        )
        if existing_index is None:
            items.append(item)
        else:
            items[existing_index] = item
        self.write_collection(collection, items)
        return item

    def delete(self, collection: str, item_id: str, key: str = "id") -> bool:
        items = self.read_collection(collection)
        next_items = [row for row in items if row.get(key) != item_id]
        if len(next_items) == len(items):
            return False
        self.write_collection(collection, next_items)
        return True

    def clear_all(self) -> None:
        for path in Path(self.base_dir).glob("*.json"):
            path.unlink(missing_ok=True)


@dataclass(slots=True)
class TripRepository:
    store: JsonFileStore
    collection: str = "trips"

    def list(self) -> list[dict[str, Any]]:
        return self.store.read_collection(self.collection)

    def get(self, trip_id: str) -> dict[str, Any] | None:
        for item in self.list():
            if item.get("id") == trip_id:
                return item
        return None

    def create(self, trip: dict[str, Any]) -> dict[str, Any]:
        return self.store.upsert(self.collection, trip)

    def update(self, trip_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        current = self.get(trip_id)
        if current is None:
            return None
        current.update(patch)
        current["updated_at"] = datetime.utcnow().isoformat()
        self.store.upsert(self.collection, current)
        return current

    def delete(self, trip_id: str) -> bool:
        return self.store.delete(self.collection, trip_id)
