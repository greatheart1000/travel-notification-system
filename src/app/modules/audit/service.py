from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.modules.audit.models import AuditLog
from app.modules.integration.persistence import JsonFileStore


@dataclass(slots=True)
class AuditLogRepository:
    """MVP repository for audit logs with optional JSON persistence."""

    logs: list[AuditLog] = field(default_factory=list)
    store: JsonFileStore | None = None
    collection: str = "audit_logs"

    def __post_init__(self) -> None:
        if self.store is None:
            return
        self.logs = [AuditLog(**row) for row in self.store.read_collection(self.collection)]

    def _flush(self) -> None:
        if self.store is None:
            return
        payload = [
            {
                "id": log.id,
                "created_at": log.created_at,
                "updated_at": log.updated_at,
                "operator_id": log.operator_id,
                "action": log.action,
                "target": log.target,
                "detail": log.detail,
            }
            for log in self.logs
        ]
        self.store.write_collection(self.collection, payload)

    def add(self, log: AuditLog) -> AuditLog:
        self.logs.append(log)
        self._flush()
        return log

    def list_by_target(self, target: str) -> list[AuditLog]:
        return [log for log in self.logs if log.target == target]

    def list_by_target_payload(self, target: str) -> list[dict[str, Any]]:
        return [asdict(log) for log in self.list_by_target(target)]


class AuditService:
    def __init__(self, repository: AuditLogRepository | None = None) -> None:
        self.repository = repository or AuditLogRepository()

    def record(
        self, operator_id: str, action: str, target: str, detail: dict | None = None
    ) -> AuditLog:
        entry = AuditLog(operator_id=operator_id, action=action, target=target, detail=detail or {})
        return self.repository.add(entry)
