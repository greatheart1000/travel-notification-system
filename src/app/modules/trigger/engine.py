from __future__ import annotations

from app.modules.trigger.models import TriggerRule


class TriggerEngine:
    """按规则判断是否触发通知。"""

    def evaluate(self, rule: TriggerRule, context: dict) -> bool:
        if rule.is_mandatory:
            return True
        for key, expected in rule.conditions.items():
            if context.get(key) != expected:
                return False
        return True
