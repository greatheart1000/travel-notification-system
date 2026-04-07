from __future__ import annotations

from dataclasses import dataclass

from app.core.models import BaseRecord


@dataclass(slots=True)
class ComplaintEvent(BaseRecord):
    team_id: str = ""
    customer_id: str = ""
    source_text: str = ""
    sentiment_score: float = 0.0
    escalated: bool = False
