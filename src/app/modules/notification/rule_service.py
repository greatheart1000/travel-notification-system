from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.modules.integration.persistence import JsonFileStore

UTC = timezone.utc

STAGE_ALIASES: dict[str, str] = {
    "pre_trip": "pre_trip",
    "before_departure": "pre_trip",
    "before": "pre_trip",
    "行前": "pre_trip",
    "in_trip": "in_trip",
    "on_trip": "in_trip",
    "during": "in_trip",
    "行中": "in_trip",
    "post_trip": "post_trip",
    "after_trip": "post_trip",
    "after": "post_trip",
    "行后": "post_trip",
}

TIME_SLOT_ALIASES: dict[str, str] = {
    "morning": "morning",
    "am": "morning",
    "早间": "morning",
    "afternoon": "afternoon",
    "pm": "afternoon",
    "午间": "afternoon",
    "evening": "evening",
    "night": "night",
    "晚间": "night",
    "all_day": "all_day",
    "any": "all_day",
    "anytime": "all_day",
    "全天": "all_day",
}

SCENE_ALIASES: dict[str, str] = {
    "normal": "normal",
    "default": "normal",
    "常规": "normal",
    "weather": "weather_alert",
    "weather_alert": "weather_alert",
    "天气": "weather_alert",
    "delay": "delay",
    "flight_delay": "delay",
    "延误": "delay",
    "complaint": "complaint",
    "投诉": "complaint",
    "manual": "manual",
    "人工": "manual",
}

CHANNEL_ALIASES: dict[str, str] = {
    "sms": "sms",
    "短信": "sms",
    "wechat_work_group": "wechat_work_group",
    "wechat": "wechat_work_group",
    "企业微信": "wechat_work_group",
    "email": "email",
    "邮件": "email",
}

RULE_STATUS_ALIASES: dict[str, str] = {
    "draft": "draft",
    "pending_approval": "pending_approval",
    "approved": "approved",
    "published": "published",
    "archived": "archived",
    "rejected": "rejected",
}


class RuleValidationError(ValueError):
    pass


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _normalize_enum(raw_value: str, aliases: dict[str, str], field_name: str) -> str:
    key = raw_value.strip().lower()
    normalized = aliases.get(key)
    if normalized is None:
        raise RuleValidationError(f"Invalid {field_name}: {raw_value}")
    return normalized


def normalize_stage(raw_value: str) -> str:
    return _normalize_enum(raw_value, STAGE_ALIASES, "stage")


def normalize_time_slot(raw_value: str) -> str:
    return _normalize_enum(raw_value, TIME_SLOT_ALIASES, "time_slot")


def normalize_scene(raw_value: str) -> str:
    return _normalize_enum(raw_value, SCENE_ALIASES, "scene")


def normalize_channels(values: list[str] | None) -> list[str]:
    if values is None:
        return []
    channels: list[str] = []
    for value in values:
        key = str(value).strip().lower()
        normalized = CHANNEL_ALIASES.get(key)
        if normalized is None:
            raise RuleValidationError(f"Invalid channel: {value}")
        if normalized not in channels:
            channels.append(normalized)
    return channels


def normalize_rule_status(raw_value: str) -> str:
    return _normalize_enum(raw_value, RULE_STATUS_ALIASES, "status")


@dataclass(slots=True)
class NotificationRuleRepository:
    store: JsonFileStore
    collection: str = "notification_rules"
    _rules: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for row in self.store.read_collection(self.collection):
            rule_id = str(row.get("id", "")).strip()
            if not rule_id:
                continue
            self._rules[rule_id] = self._normalize_rule(row, partial=False)

    def _persist(self) -> None:
        self.store.write_collection(self.collection, list(self._rules.values()))

    def _normalize_rule(self, payload: dict[str, Any], *, partial: bool) -> dict[str, Any]:
        normalized: dict[str, Any] = {}

        if not partial or "id" in payload:
            raw_rule_id = str(payload.get("id") or "").strip()
            normalized["id"] = raw_rule_id or f"rule-{uuid4().hex[:10]}"
        if not partial or "tenant_id" in payload:
            tenant_id = str(payload.get("tenant_id") or "").strip()
            if not tenant_id:
                raise RuleValidationError("tenant_id is required")
            normalized["tenant_id"] = tenant_id

        if not partial or "name" in payload:
            name = str(payload.get("name") or "").strip()
            if not name:
                raise RuleValidationError("name is required")
            normalized["name"] = name

        if not partial or "stage" in payload:
            stage = payload.get("stage")
            if stage is None:
                raise RuleValidationError("stage is required")
            normalized["stage"] = normalize_stage(str(stage))

        if not partial or "time_slot" in payload:
            time_slot = payload.get("time_slot")
            if time_slot is None:
                raise RuleValidationError("time_slot is required")
            normalized["time_slot"] = normalize_time_slot(str(time_slot))

        if not partial or "scene" in payload:
            scene = payload.get("scene")
            if scene is None:
                raise RuleValidationError("scene is required")
            normalized["scene"] = normalize_scene(str(scene))

        if "channels" in payload:
            normalized["channels"] = normalize_channels(payload.get("channels"))
        elif not partial:
            normalized["channels"] = []

        if "template_id" in payload:
            raw_template_id = payload.get("template_id")
            normalized["template_id"] = str(raw_template_id).strip() if raw_template_id else None
        elif not partial:
            normalized["template_id"] = None

        if "enabled" in payload:
            normalized["enabled"] = bool(payload.get("enabled"))
        elif not partial:
            normalized["enabled"] = True

        if "status" in payload:
            status = str(payload.get("status") or "").strip()
            if not status:
                raise RuleValidationError("status is required")
            normalized["status"] = normalize_rule_status(status)
        elif not partial:
            enabled = bool(normalized.get("enabled", payload.get("enabled", True)))
            normalized["status"] = "published" if enabled else "draft"

        if "priority" in payload:
            normalized["priority"] = int(payload.get("priority") or 0)
        elif not partial:
            normalized["priority"] = 100

        if "conditions" in payload:
            conditions = payload.get("conditions")
            if conditions is None:
                normalized["conditions"] = {}
            elif isinstance(conditions, dict):
                normalized["conditions"] = conditions
            else:
                raise RuleValidationError("conditions must be an object")
        elif not partial:
            normalized["conditions"] = {}

        if "trip_id" in payload:
            normalized["trip_id"] = str(payload.get("trip_id") or "")

        if not partial or "created_at" in payload:
            normalized["created_at"] = str(payload.get("created_at") or _now_iso())
        if not partial or "submitted_at" in payload:
            normalized["submitted_at"] = str(payload.get("submitted_at") or "")
        if not partial or "submitted_by" in payload:
            normalized["submitted_by"] = str(payload.get("submitted_by") or "")
        if not partial or "approved_at" in payload:
            normalized["approved_at"] = str(payload.get("approved_at") or "")
        if not partial or "approved_by" in payload:
            normalized["approved_by"] = str(payload.get("approved_by") or "")
        if not partial or "rejected_at" in payload:
            normalized["rejected_at"] = str(payload.get("rejected_at") or "")
        if not partial or "rejected_by" in payload:
            normalized["rejected_by"] = str(payload.get("rejected_by") or "")
        if not partial or "rejection_reason" in payload:
            normalized["rejection_reason"] = str(payload.get("rejection_reason") or "")
        if not partial or "published_at" in payload:
            normalized["published_at"] = str(payload.get("published_at") or "")
        if not partial or "published_by" in payload:
            normalized["published_by"] = str(payload.get("published_by") or "")

        normalized["updated_at"] = str(payload.get("updated_at") or _now_iso())
        return normalized

    def list_rules(
        self,
        *,
        tenant_id: str,
        enabled: bool | None = None,
        stage: str | None = None,
        time_slot: str | None = None,
        scene: str | None = None,
        trip_id: str | None = None,
    ) -> list[dict[str, Any]]:
        items = [item for item in self._rules.values() if item.get("tenant_id") == tenant_id]
        if enabled is not None:
            items = [item for item in items if bool(item.get("enabled")) is enabled]
        if stage is not None:
            stage_value = normalize_stage(stage)
            items = [item for item in items if item.get("stage") == stage_value]
        if time_slot is not None:
            slot_value = normalize_time_slot(time_slot)
            items = [item for item in items if item.get("time_slot") == slot_value]
        if scene is not None:
            scene_value = normalize_scene(scene)
            items = [item for item in items if item.get("scene") == scene_value]
        if trip_id is not None:
            items = [item for item in items if item.get("trip_id") == trip_id]

        return sorted(
            items,
            key=lambda item: (
                int(item.get("priority", 100)),
                str(item.get("updated_at", "")),
                str(item.get("id", "")),
            ),
        )

    def get_rule(self, rule_id: str, *, tenant_id: str) -> dict[str, Any] | None:
        rule = self._rules.get(rule_id)
        if rule is None:
            return None
        if rule.get("tenant_id") != tenant_id:
            return None
        return dict(rule)

    def create_rule(self, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = self._normalize_rule(payload, partial=False)
        rule_id = normalized["id"]
        if rule_id in self._rules:
            raise RuleValidationError(f"Rule already exists: {rule_id}")
        self._rules[rule_id] = normalized
        self._persist()
        return dict(normalized)

    def update_rule(
        self, rule_id: str, payload: dict[str, Any], *, tenant_id: str
    ) -> dict[str, Any] | None:
        current = self._rules.get(rule_id)
        if current is None:
            return None
        if current.get("tenant_id") != tenant_id:
            return None
        normalized_patch = self._normalize_rule(payload, partial=True)
        next_rule = dict(current)
        next_rule.update(normalized_patch)
        next_rule["id"] = rule_id
        next_rule["updated_at"] = _now_iso()
        self._rules[rule_id] = next_rule
        self._persist()
        return dict(next_rule)

    def delete_rule(self, rule_id: str, *, tenant_id: str) -> bool:
        rule = self._rules.get(rule_id)
        if rule is None:
            return False
        if rule.get("tenant_id") != tenant_id:
            return False
        del self._rules[rule_id]
        self._persist()
        return True

    def submit_rule(self, rule_id: str, *, tenant_id: str, operator_id: str) -> dict[str, Any] | None:
        return self._transition_status(
            rule_id=rule_id,
            tenant_id=tenant_id,
            from_status={"draft", "rejected"},
            to_status="pending_approval",
            extra={"submitted_by": operator_id, "submitted_at": _now_iso(), "rejection_reason": ""},
        )

    def approve_rule(
        self, rule_id: str, *, tenant_id: str, operator_id: str
    ) -> dict[str, Any] | None:
        return self._transition_status(
            rule_id=rule_id,
            tenant_id=tenant_id,
            from_status={"pending_approval"},
            to_status="approved",
            extra={"approved_by": operator_id, "approved_at": _now_iso()},
        )

    def reject_rule(
        self, rule_id: str, *, tenant_id: str, operator_id: str, reason: str
    ) -> dict[str, Any] | None:
        return self._transition_status(
            rule_id=rule_id,
            tenant_id=tenant_id,
            from_status={"pending_approval"},
            to_status="rejected",
            extra={"rejected_by": operator_id, "rejected_at": _now_iso(), "rejection_reason": reason},
        )

    def publish_rule(
        self, rule_id: str, *, tenant_id: str, operator_id: str
    ) -> dict[str, Any] | None:
        return self._transition_status(
            rule_id=rule_id,
            tenant_id=tenant_id,
            from_status={"approved"},
            to_status="published",
            extra={"published_by": operator_id, "published_at": _now_iso(), "enabled": True},
        )

    def _transition_status(
        self,
        *,
        rule_id: str,
        tenant_id: str,
        from_status: set[str],
        to_status: str,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        current = self._rules.get(rule_id)
        if current is None or current.get("tenant_id") != tenant_id:
            return None
        status = str(current.get("status") or "draft")
        if status not in from_status:
            raise RuleValidationError(f"invalid_status_transition:{status}->{to_status}")
        next_rule = dict(current)
        next_rule["status"] = to_status
        next_rule["updated_at"] = _now_iso()
        if extra:
            next_rule.update(extra)
        self._rules[rule_id] = next_rule
        self._persist()
        return dict(next_rule)

    def simulate(
        self,
        *,
        tenant_id: str,
        stage: str,
        time_slot: str,
        scene: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        stage_value = normalize_stage(stage)
        slot_value = normalize_time_slot(time_slot)
        scene_value = normalize_scene(scene)
        context_payload = context or {}

        candidates = [
            item
            for item in self._rules.values()
            if item.get("tenant_id") == tenant_id
            and item.get("status") == "published"
            and bool(item.get("enabled"))
            and item.get("stage") == stage_value
            and item.get("time_slot") == slot_value
            and item.get("scene") == scene_value
        ]
        matched: list[dict[str, Any]] = []
        for rule in candidates:
            conditions = rule.get("conditions") or {}
            if not self._match_conditions(conditions, context_payload):
                continue
            matched.append(
                {
                    "id": rule.get("id"),
                    "name": rule.get("name"),
                    "priority": int(rule.get("priority", 100)),
                    "channels": list(rule.get("channels") or []),
                    "template_id": rule.get("template_id"),
                }
            )

        matched.sort(key=lambda item: (item["priority"], str(item["id"])))
        conflicts: list[str] = []
        if len(matched) > 1 and matched[0]["priority"] == matched[1]["priority"]:
            conflicts.append("multiple_rules_share_top_priority")
        return {"matches": matched, "conflicts": conflicts}

    def _match_conditions(self, conditions: dict[str, Any], context: dict[str, Any]) -> bool:
        for key, expected in conditions.items():
            if context.get(key) != expected:
                return False
        return True
