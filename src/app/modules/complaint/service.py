from __future__ import annotations

from app.modules.complaint.models import ComplaintEvent


class ComplaintService:
    def detect_and_escalate(self, event: ComplaintEvent, threshold: float = -0.3) -> ComplaintEvent:
        if event.sentiment_score <= threshold:
            event.escalated = True
        return event
