from __future__ import annotations

from dataclasses import dataclass, field

from app.modules.audit.models import AuditLog


@dataclass(slots=True)
class AuditLogRepository:
    """MVP in-memory repository for audit logs."""

    logs: list[AuditLog] = field(default_factory=list)

    def add(self, log: AuditLog) -> AuditLog:
        self.logs.append(log)
        return log

    def list_by_target(self, target: str) -> list[AuditLog]:
        return [log for log in self.logs if log.target == target]


class AuditService:
    def __init__(self, repository: AuditLogRepository | None = None) -> None:
        self.repository = repository or AuditLogRepository()

    def record(self, operator_id: str, action: str, target: str, detail: dict | None = None) -> AuditLog:
        entry = AuditLog(operator_id=operator_id, action=action, target=target, detail=detail or {})
        return self.repository.add(entry)
