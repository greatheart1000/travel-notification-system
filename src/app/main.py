from __future__ import annotations

from app.api.http import run_http_server
from app.modules.complaint.models import ComplaintEvent
from app.modules.complaint.service import ComplaintService
from app.modules.notification.models import NotificationTask, NotificationTemplate
from app.modules.notification.service import NotificationService
from app.modules.survey.models import SurveyResponse
from app.modules.survey.service import SurveyService


def bootstrap_demo() -> dict:
    notification_service = NotificationService()
    complaint_service = ComplaintService()
    survey_service = SurveyService()

    template = NotificationTemplate(
        name="daily-reminder-default",
        content="{{customer_name}}，您好，明日行程请注意保暖并准时集合。",
    )
    rendered = notification_service.render(template, {"customer_name": "张三"})

    task = NotificationTask(team_id="TEAM-001", customer_id="C-001", rendered_content=rendered)
    dispatch_result = notification_service.dispatch(task)

    complaint = complaint_service.detect_and_escalate(
        ComplaintEvent(team_id="TEAM-001", customer_id="C-001", sentiment_score=-0.8)
    )
    survey = survey_service.mark_follow_up(
        SurveyResponse(team_id="TEAM-001", customer_id="C-001", score=2)
    )

    return {
        "dispatch": dispatch_result,
        "complaint_escalated": complaint.escalated,
        "survey_follow_up": survey.follow_up_required,
    }


if __name__ == "__main__":
    run_http_server()
