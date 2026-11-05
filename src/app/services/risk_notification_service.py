from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from app.core.models import Channel, NotificationType
from app.modules.integration.persistence import JsonFileStore
from app.modules.integration.weather_provider import WeatherInfo, WeatherProvider
from app.modules.notification.models import NotificationTask
from app.modules.notification.service import NotificationService
from app.modules.trigger.itinerary_service import ItineraryItem, ItineraryRiskService
from app.services.template_service import TemplateService

UTC = UTC

SPECIAL_RISK_TAG_LABELS: dict[str, str] = {
    "highland": "高原",
    "border": "边境",
    "horse_riding": "骑马",
    "skiing": "滑雪",
    "no_man_land": "无人区",
    "extreme_cold": "极寒",
}

TAG_ALIASES: dict[str, str] = {
    "高原": "highland",
    "海拔": "highland",
    "边境": "border",
    "口岸": "border",
    "骑马": "horse_riding",
    "马术": "horse_riding",
    "滑雪": "skiing",
    "雪场": "skiing",
    "无人区": "no_man_land",
    "荒漠": "no_man_land",
    "极寒": "extreme_cold",
    "严寒": "extreme_cold",
    "highland": "highland",
    "border": "border",
    "horse_riding": "horse_riding",
    "skiing": "skiing",
    "no_man_land": "no_man_land",
    "extreme_cold": "extreme_cold",
}

TRANSPORT_ABNORMAL_STATUSES = {"delayed", "cancelled", "changed", "延误", "取消", "变更"}
WEATHER_RISK_WORDS = {"雨", "雪", "暴", "冰雹", "大风", "沙尘", "冻雨", "rain", "snow", "storm", "wind"}


@dataclass(slots=True)
class RiskTrigger:
    trigger_id: str
    tenant_id: str
    trip_id: str
    team_id: str
    project_id: str
    risk_type: str
    trigger_timing: str
    scheduled_for: str
    risk_tags: list[str]
    hit_rules: list[str]
    recommendation_actions: list[str]
    weather_summary: str = ""
    transport_summary: str = ""
    itinerary_day: str = ""
    itinerary_title: str = ""


@dataclass(slots=True)
class RiskNotificationEvidence:
    evidence_id: str
    trigger_id: str
    task_id: str
    tenant_id: str
    trip_id: str
    team_id: str
    channel: str
    content: str
    status: str
    provider_message: str
    sent_at: str
    receipt_status: str = "sent"
    concierge_confirmation_status: str = "pending"
    concierge_confirmed_by: str = ""
    concierge_confirmed_at: str = ""
    escalated: bool = False
    escalated_at: str = ""
    escalation_reason: str = ""
    risk_tags: list[str] = field(default_factory=list)
    hit_rules: list[str] = field(default_factory=list)


class RiskEvidenceRepository:
    def __init__(self, store: JsonFileStore | None = None, collection: str = "risk_notification_evidence") -> None:
        self.store = store
        self.collection = collection
        self._items: list[dict[str, Any]] = []
        if self.store is not None:
            self._items = self.store.read_collection(self.collection)

    def add(self, evidence: RiskNotificationEvidence) -> dict[str, Any]:
        payload = asdict(evidence)
        self._items.insert(0, payload)
        self._flush()
        return payload

    def list(self, *, tenant_id: str | None = None, trip_id: str | None = None) -> list[dict[str, Any]]:
        items = list(self._items)
        if tenant_id:
            items = [item for item in items if item.get("tenant_id") == tenant_id]
        if trip_id:
            items = [item for item in items if item.get("trip_id") == trip_id]
        return items

    def get(self, evidence_id: str) -> dict[str, Any] | None:
        return next((item for item in self._items if item.get("evidence_id") == evidence_id), None)

    def update(self, evidence_id: str, patch: dict[str, Any], *, tenant_id: str | None = None) -> dict[str, Any] | None:
        for index, item in enumerate(self._items):
            if item.get("evidence_id") != evidence_id:
                continue
            if tenant_id is not None and item.get("tenant_id") != tenant_id:
                return None
            updated = {**item, **patch}
            self._items[index] = updated
            self._flush()
            return updated
        return None

    def _flush(self) -> None:
        if self.store is not None:
            self.store.write_collection(self.collection, self._items)


class RiskNotificationWorkflow:
    """Special-scene risk workflow: ERP tags + QWeather 24h + WeCom delivery + confirmation."""

    def __init__(
        self,
        *,
        trip_repository: Any,
        template_service: TemplateService,
        notification_service: NotificationService,
        weather_provider: WeatherProvider,
        evidence_repository: RiskEvidenceRepository | None = None,
        audit_service: Any | None = None,
        project_notification_config_repository: Any | None = None,
        itinerary_risk_service: ItineraryRiskService | None = None,
    ) -> None:
        self.trip_repository = trip_repository
        self.template_service = template_service
        self.notification_service = notification_service
        self.weather_provider = weather_provider
        self.evidence_repository = evidence_repository or RiskEvidenceRepository()
        self.audit_service = audit_service
        self.project_notification_config_repository = project_notification_config_repository
        self.itinerary_risk_service = itinerary_risk_service or ItineraryRiskService()

    def sync_erp_risk_tags(self, trip: dict[str, Any]) -> dict[str, Any]:
        """Normalize ERP itinerary/business tags into trip-level and day-level risk fields."""
        normalized = dict(trip)
        itinerary = list(normalized.get("itinerary") or [])
        trip_tags = self._normalize_tags(
            self._extract_raw_tags(normalized, keys=("risk_tags", "business_tags", "tags", "labels"))
        )
        day_tags: list[dict[str, Any]] = []
        for day in itinerary:
            tags = self._risk_tags_for_itinerary_item(day)
            if tags:
                day_copy = dict(day)
                day_copy["risk_tags"] = sorted(tags)
                day_tags.append(day_copy)
        normalized["risk_tags"] = sorted(trip_tags | {tag for day in day_tags for tag in day["risk_tags"]})
        normalized["itinerary"] = [
            next((day for day in day_tags if str(day.get("date") or day.get("day") or "") == str(item.get("date") or item.get("day") or "")), item)
            for item in itinerary
        ]
        normalized["erp_risk_tag_synced_at"] = datetime.now(tz=UTC).isoformat()
        return normalized

    def build_triggers(
        self,
        *,
        tenant_id: str,
        now: datetime | None = None,
    ) -> list[RiskTrigger]:
        current = now or datetime.now(tz=UTC)
        triggers: list[RiskTrigger] = []
        for trip in self.trip_repository.list():
            if str(trip.get("tenant_id") or "") != tenant_id:
                continue
            if str(trip.get("status") or "") not in {"planned", "in_progress"}:
                continue
            normalized_trip = self.sync_erp_risk_tags(trip)
            weather = self._weather_for_trip(normalized_trip, tenant_id)
            triggers.extend(self._build_itinerary_tag_triggers(normalized_trip, current))
            weather_trigger = self._build_weather_trigger(normalized_trip, weather, current)
            if weather_trigger is not None:
                triggers.append(weather_trigger)
            transport_trigger = self._build_transport_trigger(normalized_trip, current)
            if transport_trigger is not None:
                triggers.append(transport_trigger)
        return self._dedupe_triggers(triggers)

    def send_due_risks(
        self,
        *,
        tenant_id: str,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        current = now or datetime.now(tz=UTC)
        sent: list[dict[str, Any]] = []
        for trigger in self.build_triggers(tenant_id=tenant_id, now=current):
            idempotency_key = f"risk:{trigger.trigger_id}:{current.date().isoformat()}"
            existing = next(
                (
                    item
                    for item in self.evidence_repository.list(tenant_id=tenant_id)
                    if item.get("trigger_id") == trigger.trigger_id
                ),
                None,
            )
            if existing is not None and str(existing.get("status") or "") == "sent":
                continue
            task = self._build_task(trigger, idempotency_key)
            result = self.notification_service.dispatch(task)
            latest_attempt = task.attempts[-1] if task.attempts else None
            status = "sent" if result.get("ok") else "manual_intervention"
            provider_message = (
                latest_attempt.provider_message
                if latest_attempt
                else str(result.get("reason") or "")
            )
            evidence_patch = {
                "task_id": task.id,
                "channel": task.primary_channel.value,
                "content": task.rendered_content,
                "status": status,
                "provider_message": provider_message,
                "sent_at": current.isoformat(),
                "receipt_status": "provider_accepted" if result.get("ok") else "send_failed",
                "risk_tags": trigger.risk_tags,
                "hit_rules": trigger.hit_rules,
            }
            if existing is not None:
                updated = self.evidence_repository.update(
                    str(existing["evidence_id"]), evidence_patch
                )
                evidence = updated or existing
            else:
                evidence = self.evidence_repository.add(
                    RiskNotificationEvidence(
                        evidence_id=f"evidence-{uuid4().hex[:10]}",
                        trigger_id=trigger.trigger_id,
                        tenant_id=trigger.tenant_id,
                        trip_id=trigger.trip_id,
                        team_id=trigger.team_id,
                        **evidence_patch,
                    )
                )
            sent.append(evidence)
            self._audit(
                "risk_notification_sent",
                trigger.trip_id,
                {
                    "trigger_id": trigger.trigger_id,
                    "team_id": trigger.team_id,
                    "risk_type": trigger.risk_type,
                    "risk_tags": trigger.risk_tags,
                    "channel": task.primary_channel.value,
                    "status": status,
                },
            )
        return {"sent_count": len(sent), "items": sent}

    def confirm(
        self,
        evidence_id: str,
        *,
        tenant_id: str,
        operator_id: str,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        current = now or datetime.now(tz=UTC)
        existing = self.evidence_repository.get(evidence_id)
        if existing is None or str(existing.get("tenant_id") or "") != tenant_id:
            raise KeyError(evidence_id)
        updated = self.evidence_repository.update(
            evidence_id,
            {
                "concierge_confirmation_status": "confirmed",
                "concierge_confirmed_by": operator_id,
                "concierge_confirmed_at": current.isoformat(),
            },
            tenant_id=tenant_id,
        )
        if updated is None:
            raise KeyError(evidence_id)
        self._audit(
            "risk_notification_confirmed",
            str(updated.get("trip_id") or ""),
            {"evidence_id": evidence_id, "operator_id": operator_id},
        )
        return updated

    def escalate_overdue(
        self,
        *,
        tenant_id: str,
        now: datetime | None = None,
        timeout_minutes: int = 15,
    ) -> list[dict[str, Any]]:
        current = now or datetime.now(tz=UTC)
        escalated: list[dict[str, Any]] = []
        for item in self.evidence_repository.list(tenant_id=tenant_id):
            if item.get("concierge_confirmation_status") != "pending" or item.get("escalated"):
                continue
            try:
                sent_at = datetime.fromisoformat(str(item.get("sent_at") or "").replace("Z", "+00:00"))
            except ValueError:
                continue
            if current - sent_at < timedelta(minutes=timeout_minutes):
                continue
            updated = self.evidence_repository.update(
                str(item["evidence_id"]),
                {
                    "concierge_confirmation_status": "overdue",
                    "escalated": True,
                    "escalated_at": current.isoformat(),
                    "escalation_reason": f"concierge_not_confirmed_within_{timeout_minutes}_minutes",
                },
            )
            if updated is not None:
                escalated.append(updated)
                self._audit("risk_notification_escalated", str(updated.get("trip_id") or ""), {"evidence_id": updated.get("evidence_id"), "timeout_minutes": timeout_minutes})
        return escalated

    def _build_itinerary_tag_triggers(self, trip: dict[str, Any], now: datetime) -> list[RiskTrigger]:
        triggers: list[RiskTrigger] = []
        today = now.date()
        for item in list(trip.get("itinerary") or []):
            item_date = self._parse_item_date(item, trip)
            if item_date is None:
                continue
            delta = (item_date - today).days
            if delta not in {0, 1}:
                continue
            tags = sorted(self._risk_tags_for_itinerary_item(item) | set(trip.get("risk_tags") or []))
            special_tags = [tag for tag in tags if tag in SPECIAL_RISK_TAG_LABELS]
            if not special_tags:
                continue
            timing = "current_day" if delta == 0 else "previous_day"
            triggers.append(
                RiskTrigger(
                    trigger_id=f"{trip.get('id')}:{item_date.isoformat()}:special:{'-'.join(special_tags)}:{timing}",
                    tenant_id=str(trip.get("tenant_id") or ""),
                    trip_id=str(trip.get("id") or ""),
                    team_id=str(trip.get("team_id") or trip.get("team") or ""),
                    project_id=str(trip.get("project_id") or trip.get("team_id") or trip.get("team") or ""),
                    risk_type="special_scene",
                    trigger_timing=timing,
                    scheduled_for=item_date.isoformat(),
                    risk_tags=special_tags,
                    hit_rules=[f"erp_tag:{tag}" for tag in special_tags],
                    recommendation_actions=[self._recommendation_for_tag(tag) for tag in special_tags],
                    itinerary_day=str(item.get("day") or item_date.isoformat()),
                    itinerary_title=str(
                        item.get("title")
                        or item.get("summary")
                        or item.get("route")
                        or "特殊风险行程"
                    ),
                )
            )
        return triggers

    def _build_weather_trigger(self, trip: dict[str, Any], weather: WeatherInfo, now: datetime) -> RiskTrigger | None:
        hit_rules: list[str] = []
        actions: list[str] = []
        if weather.warning_level in {"yellow", "orange", "red", "warning"}:
            hit_rules.append(f"qweather_warning:{weather.warning_level}")
            actions.append("请提前在群内同步天气预警，并提醒游客携带雨具/保暖物资")
        for hour in weather.hourly_forecast[:24]:
            text = str(hour.get("text") or hour.get("condition") or "")
            temp = self._safe_float(hour.get("temp"), default=weather.temperature)
            wind_scale = self._safe_int(hour.get("windScale") or hour.get("wind_scale"), default=0)
            if any(word.lower() in text.lower() for word in WEATHER_RISK_WORDS):
                hit_rules.append("qweather_24h_abnormal_condition")
            if temp <= -15:
                hit_rules.append("qweather_24h_extreme_cold")
            if wind_scale >= 7:
                hit_rules.append("qweather_24h_strong_wind")
        hit_rules = sorted(set(hit_rules))
        if not hit_rules:
            return None
        if not actions:
            actions.append("请按未来24小时天气异常提前调整行程节奏，并在群内发送安全提示")
        return RiskTrigger(
            trigger_id=f"{trip.get('id')}:{now.date().isoformat()}:weather24h:{'-'.join(hit_rules)}",
            tenant_id=str(trip.get("tenant_id") or ""),
            trip_id=str(trip.get("id") or ""),
            team_id=str(trip.get("team_id") or trip.get("team") or ""),
            project_id=str(trip.get("project_id") or trip.get("team_id") or trip.get("team") or ""),
            risk_type="weather_24h",
            trigger_timing="within_24h",
            scheduled_for=now.date().isoformat(),
            risk_tags=["weather_24h"],
            hit_rules=hit_rules,
            recommendation_actions=actions,
            weather_summary=self._weather_summary(weather),
        )

    def _build_transport_trigger(self, trip: dict[str, Any], now: datetime) -> RiskTrigger | None:
        updates = list(trip.get("flight_updates") or []) + list(trip.get("transport_updates") or [])
        abnormal = [item for item in updates if str(item.get("status") or "").strip().lower() in TRANSPORT_ABNORMAL_STATUSES or str(item.get("status") or "").strip() in TRANSPORT_ABNORMAL_STATUSES]
        if not abnormal:
            return None
        summary = "；".join(
            f"{item.get('type', '交通')} {item.get('code', '')} {item.get('status', '')}".strip()
            for item in abnormal[:3]
        )
        return RiskTrigger(
            trigger_id=f"{trip.get('id')}:{now.date().isoformat()}:transport:{len(abnormal)}",
            tenant_id=str(trip.get("tenant_id") or ""),
            trip_id=str(trip.get("id") or ""),
            team_id=str(trip.get("team_id") or trip.get("team") or ""),
            project_id=str(trip.get("project_id") or trip.get("team_id") or trip.get("team") or ""),
            risk_type="transport_change",
            trigger_timing="realtime_change",
            scheduled_for=now.date().isoformat(),
            risk_tags=["transport_change"],
            hit_rules=["erp_transport_status_changed"],
            recommendation_actions=["请同步航班/大交通变动，并核对接送机与集合时间安排"],
            transport_summary=summary,
        )

    def _build_task(self, trigger: RiskTrigger, idempotency_key: str) -> NotificationTask:
        template = self.template_service.pick_notification_template(
            tenant_id=trigger.tenant_id,
            project_id=trigger.project_id,
            stage="in_trip",
            time_slot="all_day",
            scene="weather_alert" if trigger.risk_type == "weather_24h" else "manual",
            channel=Channel.WECHAT_WORK_GROUP.value,
        )
        variables = {
            "project_name": trigger.project_id or trigger.team_id or "旅行团",
            "customer_name": "各位游客",
            "destination": "",
            "alert_title": self._trigger_title(trigger),
            "weather_text": trigger.weather_summary or trigger.transport_summary or "请关注群内风险提醒",
            "risk_tags": "、".join(SPECIAL_RISK_TAG_LABELS.get(tag, tag) for tag in trigger.risk_tags),
            "itinerary_title": trigger.itinerary_title,
            "recommendation_actions": "；".join(trigger.recommendation_actions),
        }
        if template is not None:
            try:
                content = self.template_service.render_notification(template, variables)
            except ValueError:
                content = self._fallback_content(trigger)
        else:
            content = self._fallback_content(trigger)
        return NotificationTask(
            tenant_id=trigger.tenant_id,
            project_id=trigger.project_id,
            team_id=trigger.team_id,
            trip_id=trigger.trip_id,
            customer_id=trigger.team_id,
            notification_type=NotificationType.RISK_ALERT,
            primary_channel=Channel.WECHAT_WORK_GROUP,
            fallback_channel=None,
            rendered_content=content,
            idempotency_key=idempotency_key,
            provider_context={
                "risk_trigger_id": trigger.trigger_id,
                "risk_type": trigger.risk_type,
                "team_id": trigger.team_id,
            },
        )

    def _weather_for_trip(self, trip: dict[str, Any], tenant_id: str) -> WeatherInfo:
        context = dict(trip)
        if self.project_notification_config_repository is not None:
            project_id = str(trip.get("project_id") or trip.get("team_id") or trip.get("team") or "")
            project_config = self.project_notification_config_repository.get(project_id, tenant_id=tenant_id)
            context = {**(project_config or {}), **trip}
        return self.weather_provider.get_weather(str(trip.get("destination") or ""), location_context=context)

    def _risk_tags_for_itinerary_item(self, item: dict[str, Any]) -> set[str]:
        raw_tags = self._extract_raw_tags(item, keys=("risk_tags", "business_tags", "tags", "labels"))
        tags = self._normalize_tags(raw_tags)
        title_text = " ".join(
            str(item.get(key) or "")
            for key in ("title", "summary", "route", "transport")
        )
        description_text = " ".join(
            str(item.get(key) or "")
            for key in ("description", "content", "remark", "hotel")
        )
        report = self.itinerary_risk_service.build_report(
            [
                ItineraryItem(
                    day=str(item.get("day") or item.get("date") or ""),
                    title=title_text,
                    description=description_text,
                    distance_km=int(item.get("distance_km") or 0),
                    estimated_drive_hours=float(item.get("estimated_drive_hours") or 0),
                )
            ],
            checklist={},
        )
        return tags | set(report.risk_tags)

    def _stringify_erp_field(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, dict):
            return " ".join(self._stringify_erp_field(item) for item in value.values())
        if isinstance(value, str):
            return value
        if isinstance(value, Iterable):
            return " ".join(self._stringify_erp_field(item) for item in value)
        return str(value)

    def _parse_item_date(self, item: dict[str, Any], trip: dict[str, Any]) -> Any | None:
        raw_date = str(item.get("date") or item.get("service_date") or "").strip()
        if raw_date:
            try:
                return datetime.fromisoformat(raw_date[:10]).date()
            except ValueError:
                return None
        raw_day = str(item.get("day") or "").strip().upper().replace("DAY", "D")
        if raw_day.startswith("D") and raw_day[1:].isdigit():
            try:
                start = datetime.fromisoformat(str(trip.get("start_date") or "")[:10]).date()
            except ValueError:
                return None
            return start + timedelta(days=int(raw_day[1:]) - 1)
        return None

    def _extract_raw_tags(self, payload: dict[str, Any], *, keys: Iterable[str]) -> list[str]:
        values: list[str] = []
        for key in keys:
            raw = payload.get(key)
            if raw is None:
                continue
            if isinstance(raw, str):
                values.extend([part.strip() for part in raw.replace("/", ",").replace("，", ",").split(",")])
            elif isinstance(raw, Iterable):
                values.extend(str(item).strip() for item in raw)
        return [value for value in values if value]

    def _normalize_tags(self, raw_tags: Iterable[str]) -> set[str]:
        normalized: set[str] = set()
        for raw in raw_tags:
            value = str(raw).strip()
            lower = value.lower()
            if lower in TAG_ALIASES:
                normalized.add(TAG_ALIASES[lower])
                continue
            for token, tag in TAG_ALIASES.items():
                if token in value:
                    normalized.add(tag)
        return normalized

    def _dedupe_triggers(self, triggers: list[RiskTrigger]) -> list[RiskTrigger]:
        seen: set[str] = set()
        result: list[RiskTrigger] = []
        for trigger in triggers:
            if trigger.trigger_id in seen:
                continue
            seen.add(trigger.trigger_id)
            result.append(trigger)
        return result

    def _weather_summary(self, weather: WeatherInfo) -> str:
        parts = [weather.destination, weather.condition, f"{weather.temperature:.1f}°C"]
        if weather.alert_title:
            parts.append(weather.alert_title)
        elif weather.warning_level:
            parts.append(f"{weather.warning_level}级预警")
        return "，".join(part for part in parts if part)

    def _trigger_title(self, trigger: RiskTrigger) -> str:
        mapping = {
            "special_scene": "特殊行程风险提示",
            "weather_24h": "未来24小时天气异常预警",
            "transport_change": "航班/大交通变动提醒",
        }
        return mapping.get(trigger.risk_type, "行程风险提示")

    def _fallback_content(self, trigger: RiskTrigger) -> str:
        risk_tags = "、".join(SPECIAL_RISK_TAG_LABELS.get(tag, tag) for tag in trigger.risk_tags)
        context = trigger.weather_summary or trigger.transport_summary or trigger.itinerary_title
        actions = "；".join(trigger.recommendation_actions)
        return f"【{self._trigger_title(trigger)}】{risk_tags or '风险'}：{context}。{actions}。请以管家和司导现场通知为准。"

    def _recommendation_for_tag(self, tag: str) -> str:
        mapping = {
            "highland": "提醒游客避免剧烈运动，关注高反症状并备好氧气/药品",
            "border": "提醒游客随身携带证件，遵守边境管理与拍摄规定",
            "horse_riding": "提醒游客佩戴护具，听从马队和司导安全指引",
            "skiing": "提醒游客确认装备尺码和护具，避免超能力范围滑行",
            "no_man_land": "提醒游客不得擅自离队，提前确认补给和通信保障",
            "extreme_cold": "提醒游客加强保暖，准备手套帽子和防滑鞋",
        }
        return mapping.get(tag, "请管家提前确认风险提示并同步司导")

    def _safe_float(self, value: Any, *, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _safe_int(self, value: Any, *, default: int = 0) -> int:
        try:
            return int(str(value).split("-")[0])
        except (TypeError, ValueError):
            return default

    def _audit(self, action: str, target: str, detail: dict[str, Any]) -> None:
        if self.audit_service is None:
            return
        self.audit_service.record(operator_id="risk_workflow", action=action, target=target, detail=detail)
