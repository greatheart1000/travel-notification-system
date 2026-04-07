from __future__ import annotations

from dataclasses import dataclass

from app.core.models import BaseRecord


@dataclass(slots=True)
class SurveyResponse(BaseRecord):
    team_id: str = ""
    customer_id: str = ""
    score: int = 5
    comment: str = ""
    follow_up_required: bool = False
