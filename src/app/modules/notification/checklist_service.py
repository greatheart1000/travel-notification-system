from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone


@dataclass(slots=True)
class ChecklistTask:
    code: str
    description: str
    mandatory: bool = False
    confirmed: bool = False


@dataclass(slots=True)
class DailyChecklist:
    trip_id: str
    generated_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    tasks: list[ChecklistTask] = field(default_factory=list)


class ChecklistService:
    """导游任务台：高风险任务强确认 + 超时升级。"""

    def build_for_risk_tags(self, trip_id: str, risk_tags: set[str]) -> DailyChecklist:
        tasks = [ChecklistTask(code="daily_brief", description="发送当日行程播报", mandatory=False)]
        if "horse_riding" in risk_tags:
            tasks.append(
                ChecklistTask(code="horse_riding_safety", description="骑马安全讲解", mandatory=True)
            )
        if "skiing" in risk_tags:
            tasks.append(ChecklistTask(code="skiing_gear_check", description="滑雪护具检查", mandatory=True))
        if "highland" in risk_tags:
            tasks.append(ChecklistTask(code="highland_health_tip", description="高原反应提示", mandatory=True))
        return DailyChecklist(trip_id=trip_id, tasks=tasks)

    def confirm_task(self, checklist: DailyChecklist, task_code: str) -> DailyChecklist:
        for task in checklist.tasks:
            if task.code == task_code:
                task.confirmed = True
                return checklist
        raise ValueError(f"task_not_found:{task_code}")

    def needs_escalation(self, checklist: DailyChecklist, now: datetime, timeout_minutes: int = 30) -> bool:
        deadline = checklist.generated_at + timedelta(minutes=timeout_minutes)
        pending_mandatory = any(task.mandatory and not task.confirmed for task in checklist.tasks)
        return pending_mandatory and now >= deadline
