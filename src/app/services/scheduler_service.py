from __future__ import annotations

import logging
import os
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.models import Channel, NotificationType
from app.modules.integration.weather_provider import WeatherInfo, WeatherProvider
from app.modules.notification.models import NotificationTask

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
        minute, hour = _parse_cron(os.getenv("NOTIFICATION_MORNING_CRON", "0 8 * * *"), 8)
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
            stage = self._resolve_stage(trip, today)
            if stage is None:
                continue

            guests = trip.get("guests", [])
            if not guests:
                continue

            project_config = self._load_project_config(trip)
            weather_info = self.weather_provider.get_weather(
                str(trip.get("destination", "")),
                location_context=self._build_weather_context(trip, project_config),
            )
            scene = self._resolve_scene(weather_info, project_config)
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

            for guest in guests:
                phone = str(guest.get("phone", "")).strip()
                if not phone:
                    continue

                idempotency_key = (
                    f"auto:{time_slot}:{stage}:{scene}:{trip.get('id')}:{phone}:{today.isoformat()}"
                )
                if self.ctx.idempotency_store.is_processed(idempotency_key):
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
                    primary_channel=template.channel,
                    fallback_channel=Channel.WECHAT_WORK_GROUP,
                    provider_context={
                        "sms_sign_name": template.sms_sign_name
                        or str((project_config or {}).get("sms_sign_name") or ""),
                        "provider_template_code": self._resolve_provider_template_code(
                            template,
                            scene,
                            project_config,
                        ),
                    },
                )
                self.ctx.notification_tasks[task.id] = task
                self.ctx.notification_service.dispatch(task)
                self.ctx.idempotency_store.mark(idempotency_key)

            self.ctx.audit_service.record(
                operator_id="system_scheduler",
                action="auto_notification_dispatched",
                target=str(trip.get("id", "")),
                detail={"stage": stage, "time_slot": time_slot, "scene": scene},
            )

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
        start_date = str(trip.get("start_date") or "")
        end_date = str(trip.get("end_date") or "")

        if status == "in_progress":
            return "in_trip"
        if start_date:
            trip_start = datetime.strptime(start_date, "%Y-%m-%d").date()
            if trip_start >= today:
                return "pre_trip"
        if end_date:
            trip_end = datetime.strptime(end_date, "%Y-%m-%d").date()
            if (today - trip_end).days in {0, 1}:
                return "post_trip"
        return None

    def _resolve_scene(
        self,
        weather_info: WeatherInfo,
        project_config: dict[str, object] | None,
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
        }


def init_scheduler(ctx):
    scheduler_service = AutoNotificationScheduler(ctx)
    return scheduler_service
