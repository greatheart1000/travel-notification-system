from __future__ import annotations

from dataclasses import dataclass, field

from app.core.models import BaseRecord


@dataclass(slots=True)
class AuditLog(BaseRecord):
    operator_id: str = ""
    action: str = ""
    target: str = ""
    detail: dict = field(default_factory=dict)
