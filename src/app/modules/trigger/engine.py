from __future__ import annotations

from typing import Any

from app.modules.trigger.models import TriggerRule


class TriggerEngine:
    """按规则判断是否触发通知，支持简单表达式条件。"""

    def _match_value(self, actual: Any, expected: Any) -> bool:
        if isinstance(expected, dict) and "op" in expected and "value" in expected:
            op = expected["op"]
            target = expected["value"]
            if op == "==":
                return actual == target
            if op == "!=":
                return actual != target
            if op == ">":
                return actual > target
            if op == ">=":
                return actual >= target
            if op == "<":
                return actual < target
            if op == "<=":
                return actual <= target
            if op == "in" and isinstance(target, list):
                return actual in target
            return False
        return actual == expected

    def evaluate(self, rule: TriggerRule, context: dict[str, Any]) -> bool:
        if rule.is_mandatory:
            return True
        for key, expected in rule.conditions.items():
            if not self._match_value(context.get(key), expected):
                return False
        return True

    def pick_first_matched(self, rules: list[TriggerRule], context: dict[str, Any]) -> TriggerRule | None:
        enabled = sorted(rules, key=lambda item: item.priority)
        for rule in enabled:
            if self.evaluate(rule, context):
                return rule
        return None
