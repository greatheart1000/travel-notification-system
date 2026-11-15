from __future__ import annotations

from app.api.http import _build_context
from app.modules.integration.persistence import JsonFileStore


def test_build_context_shares_idempotency_store(tmp_path) -> None:
    ctx = _build_context(store=JsonFileStore(base_dir=tmp_path))

    assert ctx.idempotency_store is ctx.notification_service.idempotency_store


def test_build_context_exposes_scheduler_service_slot(tmp_path) -> None:
    ctx = _build_context(store=JsonFileStore(base_dir=tmp_path))

    assert ctx.scheduler_service is not None
    assert ctx.scheduler_service.ctx is ctx
