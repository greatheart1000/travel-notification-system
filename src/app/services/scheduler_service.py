from __future__ import annotations

import asyncio
import logging
import os
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.models import Channel, NotificationType
from app.modules.integration.weather_provider import WeatherInfo, WeatherProvider
from app.modules.notification.concierge_playbook import MESSAGE_TEMPLATES
from app.modules.notification.idempotency import IdempotencyStore
from app.modules.notification.models import NotificationTask
from app.modules.notification.policy import NotificationPolicy, PolicyDecision

logger = logging.getLogger(__name__)


def _parse_cron(expr: str, default_hour: int) -> tuple[int, int]:
    raw = expr.strip()
    if not raw:
        return 0, default_hour
    parts = raw.split()
    if len(parts) != 5:
        return 0, default_hour
    minute = int(parts[0])
    hour = int(parts[1])
    return minute, hour


class AutoNotificationScheduler:
    def __init__(self, ctx, scheduler: AsyncIOScheduler | None = None):
        self.ctx = ctx
        self.weather_provider = getattr(ctx, "weather_provider", None) or WeatherProvider()
        self.scheduler = scheduler or AsyncIOScheduler(
            timezone=os.getenv("NOTIFICATION_TIMEZONE", "Asia/Shanghai")
        )
        self._register_cron_jobs()

    def _register_cron_jobs(self) -> None:
        minute, hour = _parse_cron(os.getenv("NOTIFICATION_MORNING_CRON", "30 7 * * *"), 7)
        self.scheduler.add_job(
            self.run_morning_slot,
            "cron",
            id="notification_morning",
            hour=hour,
            minute=minute,
        )

        minute, hour = _parse_cron(os.getenv("NOTIFICATION_NOON_CRON", "0 12 * * *"), 12)
        self.scheduler.add_job(
            self.run_noon_slot,
            "cron",
            id="notification_noon",
            hour=hour,
            minute=minute,
        )

        minute, hour = _parse_cron(os.getenv("NOTIFICATION_EVENING_CRON", "0 19 * * *"), 19)
        self.scheduler.add_job(
            self.run_evening_slot,
            "cron",
            id="notification_evening",
            hour=hour,
            minute=minute,
        )

        queue_interval = int(os.getenv("NOTIFICATION_QUEUE_INTERVAL_SECONDS", "5"))
        self.scheduler.add_job(
            self.run_dispatch_queue,
            "interval",
            id="notification_async_dispatch",
            seconds=max(queue_interval, 1),
        )

    async def run_dispatch_queue(self) -> None:
        """Drain the persistent async-dispatch outbox without blocking the event loop."""
        service = getattr(self.ctx, "async_dispatch_service", None)
        if service is None:
            return
        try:
            await asyncio.to_thread(
                service.run_due_jobs,
                self.ctx.notification_tasks,
            )
        except Exception as exc:  # noqa: BLE001 - queue worker must not die
            logger.error("[AutoNotificationScheduler] async dispatch queue failed: %s", exc)

    def start(self) -> None:
        self.scheduler.start()
        logger.info("AutoNotificationScheduler started with morning/noon/evening cron jobs.")

    def stop(self) -> None:
        self.scheduler.shutdown(wait=False)
        logger.info("AutoNotificationScheduler stopped.")

    async def run_morning_slot(self) -> None:
        await self.check_and_send_notifications_for_slot("morning")

    async def run_noon_slot(self) -> None:
        await self.check_and_send_notifications_for_slot("afternoon")

    async def run_evening_slot(self) -> None:
        await self.check_and_send_notifications_for_slot("evening")

    async def check_and_send_notifications(self) -> None:
        await self.check_and_send_notifications_for_slot("morning")

    async def check_and_send_notifications_for_slot(
        self,
        time_slot: str,
        *,
        now: datetime | None = None,
    ) -> None:
        logger.info("[AutoNotificationScheduler] Running slot=%s scan", time_slot)

        try:
            trips = self.ctx.trip_repository.list()
        except Exception as exc:  # pragma: no cover
            logger.error("[AutoNotificationScheduler] Error fetching trips: %s", exc)
            return

        current_time = now or datetime.now(tz=UTC)
        today = current_time.date()

        for trip in trips:
            try:
                self._process_trip(
                    trip,
                    time_slot=time_slot,
                    current_time=current_time,
                    today=today,
                )
            except Exception as exc:  # noqa: BLE001 - one trip must not stop the batch
                logger.exception(
                    "[AutoNotificationScheduler] trip=%s failed: %s",
                    trip.get("id"),
                    exc,
                )
                try:
                    self.ctx.audit_service.record(
                        operator_id="system_scheduler",
                        action="auto_notification_failed",
                        target=str(trip.get("id", "")),
                        detail={"time_slot": time_slot, "error": str(exc)},
                    )
                except Exception:  # noqa: BLE001 - audit failure must not mask original
                    pass

    def _process_trip(
        self,
        trip: dict,
        *,
        time_slot: str,
        current_time: datetime,
        today,
    ) -> None:  # noqa: ANN001
        stage = self._resolve_stage(trip, today)
        if stage is None:
            return

        guests = trip.get("guests", [])
        scene_for_audit = "normal"
        if guests:
            project_config = self._load_project_config(trip)
            try:
                weather_info = self.weather_provider.get_weather(
                    str(trip.get("destination", "")),
                    location_context=self._build_weather_context(trip, project_config),
                )
            except Exception as exc:  # noqa: BLE001 - weather must not stop notifications
                logger.warning(
                    "[AutoNotificationScheduler] weather unavailable for trip=%s: %s",
                    trip.get("id"),
                    exc,
                )
                weather_info = WeatherInfo(
                    destination=str(trip.get("destination", "")),
                    condition="天气数据暂不可用",
                    temperature=0.0,
                    source="fallback",
                )

            scene = self._resolve_scene(weather_info, project_config, trip)
            scene_for_audit = scene
            policy_decision = self._policy_decision(
                trip, stage, time_slot, scene, today, current_time
            )
            if (
                policy_decision is not None
                and policy_decision.configured
                and not policy_decision.allowed
            ):
                return
            primary_channel = self._policy_channel(policy_decision)
            template = self.ctx.template_service.pick_notification_template(
                tenant_id=str(trip.get("tenant_id", "tenant-a")),
                project_id=self._resolve_project_id(trip),
                stage=stage,
                time_slot=time_slot,
                scene=scene,
                channel=primary_channel.value,
            )
            if template is None and primary_channel is not Channel.SMS:
                template = self.ctx.template_service.pick_notification_template(
                    tenant_id=str(trip.get("tenant_id", "tenant-a")),
                    project_id=self._resolve_project_id(trip),
                    stage=stage,
                    time_slot=time_slot,
                    scene=scene,
                    channel=Channel.SMS.value,
                )
            if template is None:
                template = self.ctx.template_service.ensure_default_template(
                    tenant_id=str(trip.get("tenant_id", "tenant-a"))
                )

            notification_type = self._resolve_notification_type(stage, scene)
            weather_text = self._build_weather_text(weather_info)
            idempotency_store = self._idempotency_store()

            for guest in guests:
                phone = str(guest.get("phone", "")).strip()
                if not phone:
                    continue

                idempotency_key = (
                    f"auto:{time_slot}:{stage}:{scene}:"
                    f"{trip.get('tenant_id', '')}:{trip.get('id')}:{phone}:{today.isoformat()}"
                )
                if idempotency_store.terminal(idempotency_key):
                    continue

                variables = self._build_variables(
                    trip=trip,
                    guest=guest,
                    weather_info=weather_info,
                    weather_text=weather_text,
                    current_time=current_time,
                )
                rendered = self.ctx.template_service.render_notification(template, variables)
                task = NotificationTask(
                    tenant_id=str(trip.get("tenant_id", "tenant-a")),
                    project_id=self._resolve_project_id(trip),
                    team_id=str(trip.get("team_id") or trip.get("team") or ""),
                    trip_id=str(trip.get("id", "")),
                    customer_id=phone,
                    rendered_content=rendered,
                    idempotency_key=idempotency_key,
                    notification_type=notification_type,
                    primary_channel=primary_channel,
                    fallback_channel=(
                        Channel.SMS
                        if primary_channel is Channel.WECHAT_WORK_GROUP
                        else Channel.WECHAT_WORK_GROUP
                    ),
                    provider_context={
                        "sms_sign_name": template.sms_sign_name
                        or str((project_config or {}).get("sms_sign_name") or ""),
                        "provider_template_code": self._resolve_provider_template_code(
                            template,
                            scene,
                            project_config,
                        ),
                        "webhook_url": str(trip.get("webhook_url") or ""),
                    },
                )
                self.ctx.notification_tasks[task.id] = task
                # Dispatcher owns idempotency marking: success marks the key,
                # failure leaves it retryable for the next scheduler run.
                self.ctx.notification_service.dispatch(task)

        # 在途行程额外发送分岗位话术到企业微信群
        if stage == "in_trip" and time_slot in ("morning", "afternoon"):
            effective_slot = "morning" if time_slot == "morning" else "noon"
            self._send_staff_role_messages(trip, effective_slot, current_time)

        self.ctx.audit_service.record(
            operator_id="system_scheduler",
            action="auto_notification_dispatched",
            target=str(trip.get("id", "")),
            detail={"stage": stage, "time_slot": time_slot, "scene": scene_for_audit},
        )

    def _policy_decision(
        self,
        trip: dict,
        stage: str,
        time_slot: str,
        scene: str,
        today,
        current_time: datetime,
    ) -> PolicyDecision | None:  # noqa: ANN001
        rule_repository = getattr(self.ctx, "notification_rule_repository", None)
        if rule_repository is None:
            return None
        policy = NotificationPolicy(rule_repository)
        decision = policy.resolve(
            tenant_id=str(trip.get("tenant_id", "tenant-a")),
            stage=stage,
            time_slot=time_slot,
            scene=scene,
            context={
                **trip,
                "time_node": self._resolve_time_node(trip, stage, today),
                "scene": scene,
                "time_slot": time_slot,
            },
        )
        if decision.configured and not decision.allowed:
            self.ctx.audit_service.record(
                operator_id="system_scheduler",
                action="auto_notification_blocked_by_rule",
                target=str(trip.get("id", "")),
                detail={"stage": stage, "time_slot": time_slot, "scene": scene},
            )
        return decision

    @staticmethod
    def _policy_channel(decision: PolicyDecision | None) -> Channel:
        if decision is not None and decision.channels:
            for code in decision.channels:
                if code == Channel.WECHAT_WORK_GROUP.value:
                    return Channel.WECHAT_WORK_GROUP
                if code == Channel.SMS.value:
                    return Channel.SMS
        return Channel.SMS

    def _resolve_time_node(self, trip: dict, stage: str, today) -> str:  # noqa: ANN001
        if stage == "pre_trip":
            start_date = self._parse_date(trip.get("start_date"))
            if start_date is not None:
                return f"出发前{(start_date - today).days}天"
            return "行前"
        if stage == "in_trip":
            return "每日固定时段"
        if stage == "post_trip":
            return "下团即时"
        return ""

    def _resolve_project_id(self, trip: dict[str, object]) -> str:
        return str(trip.get("project_id") or trip.get("team_id") or trip.get("team") or "")

    def _load_project_config(self, trip: dict[str, object]) -> dict[str, object] | None:
        repository = getattr(self.ctx, "project_notification_config_repository", None)
        if repository is None:
            return None
        return repository.get(
            self._resolve_project_id(trip),
            tenant_id=str(trip.get("tenant_id", "tenant-a")),
        )

    def _build_weather_context(
        self,
        trip: dict[str, object],
        project_config: dict[str, object] | None,
    ) -> dict[str, object]:
        context = dict(project_config or {})
        context.update(trip)
        return context

    def _resolve_stage(self, trip: dict[str, object], today) -> str | None:  # noqa: ANN001
        status = str(trip.get("status") or "").strip().lower()
        start_date = self._parse_date(trip.get("start_date"))
        end_date = self._parse_date(trip.get("end_date"))

        if status == "cancelled":
            return None
        if status == "in_progress":
            return "in_trip"

        if start_date is not None:
            days_until_start = (start_date - today).days
            if days_until_start in self.PRE_TRIP_DAYS:
                return "pre_trip"

        if end_date is not None and (today - end_date).days in self.POST_TRIP_DAYS:
            return "post_trip"

        if start_date is not None:
            days_until_start = (start_date - today).days
            if days_until_start <= 0 and (end_date is None or today <= end_date):
                return "in_trip"

        return None

    PRE_TRIP_DAYS: tuple[int, ...] = (3, 1)
    POST_TRIP_DAYS: tuple[int, ...] = (0, 1)

    def _parse_date(self, raw: object):  # noqa: ANN201
        value = str(raw or "").strip()[:10]
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None

    def _idempotency_store(self) -> IdempotencyStore:
        store = getattr(self.ctx, "idempotency_store", None)
        if store is None:
            store = getattr(self.ctx.notification_service, "idempotency_store", None)
        if store is None:
            store = IdempotencyStore()
            setattr(self.ctx, "idempotency_store", store)
        return store

    _SCENE_TAG_MAP: dict[str, str] = {
        "骑马": "horse_riding",
        "滑雪": "ski",
        "高原": "highland",
        "边境口岸": "border",
        "极寒": "extreme_cold",
        "强紫外线": "uv_alert",
    }

    def _resolve_scene(
        self,
        weather_info: WeatherInfo,
        project_config: dict[str, object] | None,
        trip: dict[str, object] | None = None,
    ) -> str:
        thresholds = (project_config or {}).get("weather_alert_thresholds") or {}
        if not isinstance(thresholds, dict):
            thresholds = {}
        levels = thresholds.get("warning_levels", ["yellow", "orange", "red"])
        normalized_levels = {str(item).strip().lower() for item in levels if str(item).strip()}
        if weather_info.warning_level and (
            not normalized_levels or weather_info.warning_level.lower() in normalized_levels
        ):
            return "weather_alert"
        # 检查行程特殊场景标签
        tags = (trip or {}).get("scene_tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        for tag in tags:
            scene = self._SCENE_TAG_MAP.get(str(tag).strip())
            if scene:
                return scene
        return "normal"

    def _resolve_provider_template_code(
        self,
        template,
        scene: str,
        project_config: dict[str, object] | None,
    ) -> str:
        if template.provider_template_code:
            return template.provider_template_code
        if not project_config:
            return ""
        if scene == "weather_alert":
            return str(project_config.get("sms_template_code_weather_alert") or "")
        return str(project_config.get("sms_template_code_normal") or "")

    def _resolve_notification_type(self, stage: str, scene: str) -> NotificationType:
        if scene == "weather_alert":
            return NotificationType.RISK_ALERT
        mapping = {
            "pre_trip": NotificationType.PRE_TRIP_REMINDER,
            "in_trip": NotificationType.DAILY_REMINDER,
            "post_trip": NotificationType.SATISFACTION,
        }
        return mapping.get(stage, NotificationType.DAILY_REMINDER)

    def _build_weather_text(self, weather_info: WeatherInfo) -> str:
        return (
            f"{weather_info.destination}{weather_info.condition}，{weather_info.temperature:.0f}C"
        )

    def _build_variables(
        self,
        *,
        trip: dict[str, object],
        guest: dict[str, object],
        weather_info: WeatherInfo,
        weather_text: str,
        current_time: datetime,
    ) -> dict[str, str]:
        return {
            "project_name": str(trip.get("project_name") or trip.get("destination") or "旅行团"),
            "customer_name": str(guest.get("name") or "贵宾"),
            "destination": str(trip.get("destination") or ""),
            "departure_date": str(trip.get("start_date") or ""),
            "trip_date": str(trip.get("start_date") or ""),
            "weather_text": weather_text,
            "alert_title": weather_info.alert_title or "天气异常提醒",
            "flight_info": str(trip.get("flight_info") or "请留意出发前通知"),
            "highlight": str(trip.get("highlight") or "请关注群内当日安排"),
            "climate": weather_text,
            "dress_code": str(trip.get("dress_code") or "请按当地温度增减衣物"),
            "packing_tip": str(trip.get("packing_tip") or "建议携带雨具和保暖外套"),
            "concierge_name": str(trip.get("concierge_name") or "AI管家"),
            "contact_phone": str(trip.get("contact_phone") or ""),
            "time_slot": current_time.strftime("%H:%M"),
            "next_day_weather": str(trip.get("next_day_weather") or weather_text),
            "next_day_highlight": str(trip.get("next_day_highlight") or "请关注明日群内通知"),
        }


    # ── 分岗位发送 ────────────────────────────────────────────────────────────

    _SEASON_MAP: dict[int, str] = {
        1: "winter", 2: "winter", 3: "spring",
        4: "spring", 5: "spring", 6: "summer",
        7: "summer", 8: "summer", 9: "autumn",
        10: "autumn", 11: "autumn", 12: "winter",
    }

    def _resolve_season(self, dt: datetime) -> str:
        return self._SEASON_MAP.get(dt.month, "summer")

    def _render_staff_template(self, content: str, variables: dict[str, str]) -> str:
        for key, value in variables.items():
            content = content.replace("{{" + key + "}}", value)
        return content

    def _send_staff_role_messages(
        self,
        trip: dict,
        time_slot: str,
        current_time: datetime,
    ) -> None:
        season = self._resolve_season(current_time)
        slot = "morning" if time_slot == "morning" else "noon"
        if slot not in ("morning", "noon"):
            return

        roles = [
            ("manager", "manager_name", "manager_phone"),
            ("concierge", "concierge_name", "concierge_phone"),
            ("driver", "driver_name", "driver_phone"),
        ]
        idempotency_store = self._idempotency_store()
        trip_id = str(trip.get("id", ""))
        tenant_id = str(trip.get("tenant_id", "tenant-a"))
        date_key = current_time.date().isoformat()
        project_config = self._load_project_config(trip) or {}
        role_recipients = trip.get("role_recipients") or project_config.get("role_recipients") or {}
        has_explicit_recipients = bool(role_recipients)

        for role, _name_field, _phone_field in roles:
            key = f"{slot}_{season}_{role}"
            template_content = MESSAGE_TEMPLATES.get(key)
            if not template_content:
                continue

            target = self._resolve_role_target(role, role_recipients)
            if has_explicit_recipients and target is None:
                # Do not fall back to the shared group: that would deliver a
                # role-specific message to the wrong audience.
                logger.warning(
                    "[StaffDispatch] role=%s trip=%s has no configured recipient; skipped",
                    role,
                    trip_id,
                )
                continue
            channel = target["channel"] if target else Channel.WECHAT_WORK_GROUP
            address = target["address"] if target else str(trip.get("webhook_url") or "")

            staff_vars = {
                "manager_name": str(trip.get("trip_manager_name") or trip.get("concierge_name") or "负责人"),
                "manager_phone": str(trip.get("trip_manager_phone") or trip.get("contact_phone") or ""),
                "concierge_name": str(trip.get("concierge_name") or "管家"),
                "concierge_phone": str(trip.get("concierge_phone") or trip.get("contact_phone") or ""),
                "driver_name": str(trip.get("driver_name") or "司机"),
                "driver_phone": str(trip.get("driver_phone") or ""),
            }
            rendered = self._render_staff_template(template_content, staff_vars)
            idempotency_key = (
                f"staff:{slot}:{season}:{role}:{tenant_id}:{trip_id}:{date_key}"
            )
            if idempotency_store.terminal(idempotency_key):
                continue

            if channel is Channel.SMS:
                if not address:
                    logger.warning(
                        "[StaffDispatch] role=%s trip=%s SMS address missing; skipped",
                        role,
                        trip_id,
                    )
                    continue
                customer_id = address
                fallback_channel: Channel | None = Channel.WECHAT_WORK_GROUP
            else:
                customer_id = f"staff:{role}:{trip_id}"
                address = address or str(trip.get("webhook_url") or "")
                fallback_channel = None

            task = NotificationTask(
                tenant_id=tenant_id,
                project_id=self._resolve_project_id(trip),
                team_id=str(trip.get("team_id") or trip.get("team") or ""),
                trip_id=trip_id,
                customer_id=customer_id,
                rendered_content=rendered,
                idempotency_key=idempotency_key,
                notification_type=NotificationType.DAILY_REMINDER,
                primary_channel=channel,
                fallback_channel=fallback_channel,
                provider_context={
                    "role": role,
                    "webhook_url": str(address if channel is Channel.WECHAT_WORK_GROUP else trip.get("webhook_url") or ""),
                    "sms_sign_name": str(project_config.get("sms_sign_name") or ""),
                },
            )
            self.ctx.notification_tasks[task.id] = task
            result = self.ctx.notification_service.dispatch(task)
            if not result.get("ok"):
                logger.warning(
                    "[StaffDispatch] role=%s trip=%s failed: %s",
                    role,
                    trip.get("id"),
                    result.get("reason"),
                )
            else:
                logger.info("[StaffDispatch] role=%s trip=%s sent ok", role, trip.get("id"))

    _ROLE_ALIASES: dict[str, str] = {
        "manager": "manager",
        "计调": "manager",
        "dispatcher": "manager",
        "concierge": "concierge",
        "导游": "concierge",
        "guide": "concierge",
        "driver": "driver",
        "司机": "driver",
    }

    def _resolve_role_target(
        self,
        role: str,
        role_recipients: dict,
    ) -> dict[str, object] | None:
        aliases = [
            key
            for key, canonical in self._ROLE_ALIASES.items()
            if canonical == role
        ]
        recipient = None
        for key in [role, *aliases]:
            if key in role_recipients:
                recipient = role_recipients[key]
                break
        if recipient is None:
            return None
        if isinstance(recipient, str):
            value = recipient.strip()
            if not value:
                return None
            if value.startswith(("http://", "https://")):
                return {"channel": Channel.WECHAT_WORK_GROUP, "address": value}
            return {"channel": Channel.SMS, "address": value}
        if not isinstance(recipient, dict):
            return None
        channel_raw = str(recipient.get("channel") or "wechat_work_group").strip().lower()
        channel = Channel.SMS if channel_raw in {"sms", "短信"} else Channel.WECHAT_WORK_GROUP
        address = str(recipient.get("address") or recipient.get("phone") or "").strip()
        if not address:
            return None
        return {"channel": channel, "address": address}


def init_scheduler(ctx):
    scheduler_service = AutoNotificationScheduler(ctx)
    return scheduler_service
