from __future__ import annotations

from app.modules.integration.persistence import JsonFileStore
from app.modules.notification.idempotency import IdempotencyStore


def test_idempotency_store_persists_seen_keys(tmp_path) -> None:
    store = JsonFileStore(base_dir=tmp_path)

    first = IdempotencyStore(store=store)
    first.mark("tenant-a:trip-1:2026-04-12T08:00:00Z")

    second = IdempotencyStore(store=store)
    assert second.seen("tenant-a:trip-1:2026-04-12T08:00:00Z") is True
