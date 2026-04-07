from __future__ import annotations

from app.modules.survey.models import SurveyResponse


class SurveyService:
    def mark_follow_up(
        self, response: SurveyResponse, low_score_threshold: int = 3
    ) -> SurveyResponse:
        if response.score <= low_score_threshold:
            response.follow_up_required = True
        return response
