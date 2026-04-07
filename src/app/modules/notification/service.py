from __future__ import annotations

from dataclasses import asdict

from app.modules.notification.models import NotificationTask, NotificationTemplate


class NotificationService:
    """通知模块 MVP 服务：模板渲染 + 失败转人工。"""

    def render(self, template: NotificationTemplate, variables: dict[str, str]) -> str:
        content = template.content
        for key, value in variables.items():
            content = content.replace("{{" + key + "}}", value)
        return content

    def dispatch(self, task: NotificationTask) -> dict:
        # 这里仅返回结构化结果，后续接入真实网关。
        if task.primary_channel.value == "sms" and not task.rendered_content:
            task.manual_intervention_required = True
            task.retry_count += 1
            return {"ok": False, "reason": "empty_content", "task": asdict(task)}
        return {"ok": True, "task": asdict(task)}
