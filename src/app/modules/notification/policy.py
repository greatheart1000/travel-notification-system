from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.modules.notification.rule_service import NotificationRuleRepository
from app.modules.trigger.engine import TriggerEngine


@dataclass(slots=True)
class PolicyDecision:
    configured: bool
    allowed: bool
    channels: list[str] = field(default_factory=list)
    rule_ids: list[str] = field(default_factory=list)


class NotificationPolicy:
    """Evaluate tenant notification rules before dispatching a scenario.

    - No rules for the tenant/stage/scene: legacy behavior allowed.
    - Rules configured but none match time slot/conditions: blocked.
    - Matching rules: allowed, with the highest-priority rule's channels.
    """

    def __init__(self, rule_repository: NotificationRuleRepository) -> None:
        self.rule_repository = rule_repository
        self._trigger_engine = TriggerEngine()

    def resolve(
        self,
        *,
        tenant_id: str,
        stage: str,
        time_slot: str,
        scene: str,
        context: dict[str, Any] | None = None,
    ) -> PolicyDecision:
        rules = self.rule_repository.list_rules(
            tenant_id=tenant_id,
            enabled=True,
            stage=stage,
            scene=scene,
        )
        if not rules:
            return PolicyDecision(configured=False, allowed=True)

        candidates = [
            rule
            for rule in rules
            if str(rule.get("time_slot") or "") in {time_slot, "all_day"}
        ]
        payload = context or {}
        matched = [
            rule
            for rule in candidates
            if self._match_conditions(rule.get("conditions") or {}, payload)
        ]
        if not matched:
            return PolicyDecision(configured=True, allowed=False)

        matched.sort(key=lambda item: (int(item.get("priority", 100)), str(item.get("id", ""))))
        selected = matched[0]
        return PolicyDecision(
            configured=True,
            allowed=True,
            channels=list(selected.get("channels") or []),
            rule_ids=[str(rule.get("id") or "") for rule in matched],
        )

    def _match_conditions(self, conditions: Any, context: dict[str, Any]) -> bool:
        if not isinstance(conditions, dict):
            return False
        for key, expected in conditions.items():
            if not self._trigger_engine.match_value(context.get(key), expected):
                return False
        return True
