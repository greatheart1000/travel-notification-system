from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.models import UTC
from app.modules.trigger.models import TriggerRule


class TriggerEngine:
    """按规则判断是否触发通知，支持简单表达式条件。"""

    def match_value(self, actual: Any, expected: Any) -> bool:
        return self._match_value(actual, expected)

    def _match_value(self, actual: Any, expected: Any) -> bool:
        if actual is None:
            return False
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
            if op == "contains" and isinstance(actual, (list, str)):
                return target in actual
            return False
        return actual == expected

    def _is_effective(self, rule: TriggerRule, now: datetime) -> bool:
        if not rule.enabled:
            return False
        if rule.effective_from and now < rule.effective_from:
            return False
        if rule.effective_to and now > rule.effective_to:
            return False
        return True

    def evaluate(
        self, rule: TriggerRule, context: dict[str, Any], *, now: datetime | None = None
    ) -> bool:
        current = now or datetime.now(tz=UTC)
        if not self._is_effective(rule, current):
            return False
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
