from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

from app.core.models import Channel
from app.modules.notification.idempotency import IdempotencyStore
from app.modules.notification.models import NotificationTask
from app.modules.notification.service import NotificationService
from app.services.async_dispatch import AsyncDispatchService
from app.services.scheduler_service import AutoNotificationScheduler
from app.services.template_service import TemplateService
from tests.fakes import FakeChannelProvider, FakeWeatherProvider, RecordingAudit, fake_providers


class _TripRepo:
    def __init__(self, trips: list[dict[str, Any]]) -> None:
        self._trips = trips

    def list(self) -> list[dict[str, Any]]:
        return list(self._trips)


def _trip(start_offset_days: int, *, status: str = "planned", end_offset_days: int = 5) -> dict[str, Any]:
    today = datetime(2026, 5, 10, tzinfo=UTC).date()
    start = today + timedelta(days=start_offset_days)
    end = today + timedelta(days=end_offset_days)
    return {
        "id": "trip-1",
        "tenant_id": "tenant-a",
        "team_id": "TEAM-1",
        "project_id": "proj-1",
        "destination": "阿勒泰",
        "status": status,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "guests": [{"name": "张三", "phone": "13800138000"}],
    }


def _build_scheduler(
    trips: list[dict[str, Any]],
    *,
    weather: FakeWeatherProvider | None = None,
) -> tuple[AutoNotificationScheduler, FakeChannelProvider, FakeChannelProvider, SimpleNamespace]:
    template_service = TemplateService()
    template_service.create_notification_template(
        tenant_id="tenant-a",
        project_id="proj-1",
        name="行前晨间提醒",
        content="【行前提醒】{{customer_name}} {{destination}} {{weather_text}}",
        channel="sms",
        notification_type="pre_trip_reminder",
        is_active=True,
        stage="pre_trip",
        time_slot="morning",
        scene="normal",
    )
    template_service.create_notification_template(
        tenant_id="tenant-a",
        project_id="proj-1",
        name="行中晨间提醒",
        content="【行中提醒】{{customer_name}} {{destination}} {{weather_text}}",
        channel="sms",
        notification_type="daily_reminder",
        is_active=True,
        stage="in_trip",
        time_slot="morning",
        scene="normal",
    )
    sms = FakeChannelProvider(default=(True, "ok"))
    wechat = FakeChannelProvider(default=(True, "ok"))
    notification_service = NotificationService(
        providers=fake_providers(sms=sms, wechat=wechat),
        idempotency_store=IdempotencyStore(),
    )
    ctx = SimpleNamespace(
        trip_repository=_TripRepo(trips),
        template_service=template_service,
        notification_service=notification_service,
        idempotency_store=notification_service.idempotency_store,
        audit_service=RecordingAudit(),
        notification_tasks={},
        weather_provider=weather or FakeWeatherProvider(),
        project_notification_config_repository=None,
    )
    scheduler = AutoNotificationScheduler(ctx)
    return scheduler, sms, wechat, ctx


def test_pre_trip_t3_sends_once_and_is_idempotent() -> None:
    scheduler, sms, _, _ = _build_scheduler([_trip(start_offset_days=3)])
    now = datetime(2026, 5, 10, 7, 30, tzinfo=UTC)

    asyncio.run(scheduler.check_and_send_notifications_for_slot("morning", now=now))
    asyncio.run(scheduler.check_and_send_notifications_for_slot("morning", now=now))

    assert sms.call_count == 1


def test_pre_trip_t1_sends() -> None:
    scheduler, sms, _, _ = _build_scheduler([_trip(start_offset_days=1)])

    asyncio.run(
        scheduler.check_and_send_notifications_for_slot(
            "morning", now=datetime(2026, 5, 10, 7, 30, tzinfo=UTC)
        )
    )

    assert sms.call_count == 1


def test_pre_trip_t2_does_not_send() -> None:
    scheduler, sms, _, _ = _build_scheduler([_trip(start_offset_days=2)])

    asyncio.run(
        scheduler.check_and_send_notifications_for_slot(
            "morning", now=datetime(2026, 5, 10, 7, 30, tzinfo=UTC)
        )
    )

    assert sms.call_count == 0


def test_weather_provider_failure_does_not_abort_normal_send() -> None:
    weather = FakeWeatherProvider(error=RuntimeError("weather down"))
    scheduler, sms, _, _ = _build_scheduler([_trip(start_offset_days=3)], weather=weather)

    asyncio.run(
        scheduler.check_and_send_notifications_for_slot(
            "morning", now=datetime(2026, 5, 10, 7, 30, tzinfo=UTC)
        )
    )

    assert sms.call_count == 1


def test_guest_without_phone_is_skipped_without_error() -> None:
    trip = _trip(start_offset_days=3)
    trip["guests"] = [{"name": "无手机号"}]
    scheduler, sms, _, _ = _build_scheduler([trip])

    asyncio.run(
        scheduler.check_and_send_notifications_for_slot(
            "morning", now=datetime(2026, 5, 10, 7, 30, tzinfo=UTC)
        )
    )

    assert sms.call_count == 0


def test_in_trip_role_messages_are_sent_through_dispatcher_and_idempotent() -> None:
    scheduler, _, wechat, ctx = _build_scheduler([_trip(start_offset_days=0, status="in_progress")])
    now = datetime(2026, 5, 10, 7, 30, tzinfo=UTC)

    asyncio.run(scheduler.check_and_send_notifications_for_slot("morning", now=now))
    asyncio.run(scheduler.check_and_send_notifications_for_slot("morning", now=now))

    assert wechat.call_count == 3
    assert {call["provider_context"].get("role") for call in wechat.calls} == {
        "manager",
        "concierge",
        "driver",
    }
    assert all(
        str(call["customer_id"]).startswith("staff:") for call in wechat.calls
    )
    assert len(ctx.notification_tasks) >= 3


def test_pre_trip_does_not_send_role_messages() -> None:
    scheduler, _, wechat, _ = _build_scheduler([_trip(start_offset_days=3)])

    asyncio.run(
        scheduler.check_and_send_notifications_for_slot(
            "morning", now=datetime(2026, 5, 10, 7, 30, tzinfo=UTC)
        )
    )

    assert wechat.call_count == 0


def test_scheduler_registers_async_dispatch_job() -> None:
    scheduler, _, _, _ = _build_scheduler([_trip(start_offset_days=3)])

    assert scheduler.scheduler.get_job("notification_async_dispatch") is not None


def test_run_dispatch_queue_processes_queued_job() -> None:
    scheduler, sms, _, ctx = _build_scheduler([_trip(start_offset_days=3)])
    queue = AsyncDispatchService(notification_service=ctx.notification_service)
    ctx.async_dispatch_service = queue
    task = NotificationTask(
        tenant_id="tenant-a",
        team_id="TEAM-1",
        trip_id="trip-1",
        customer_id="13800138000",
        rendered_content="queued",
        primary_channel=Channel.SMS,
        fallback_channel=None,
        idempotency_key="queued:tenant-a:trip-1:1",
        max_retry=1,
    )
    ctx.notification_tasks[task.id] = task
    queue.enqueue(task, channel="sms")

    asyncio.run(scheduler.run_dispatch_queue())

    assert sms.call_count == 1
    assert queue.list_jobs(tenant_id="tenant-a")[0]["status"] == "sent"


def test_one_bad_trip_does_not_stop_other_trips() -> None:
    bad = _trip(start_offset_days=3)
    bad["id"] = "trip-bad"
    bad["project_id"] = "proj-bad"
    good = _trip(start_offset_days=3)
    good["id"] = "trip-good"
    scheduler, sms, _, _ = _build_scheduler([bad, good])
    scheduler.ctx.template_service.create_notification_template(
        tenant_id="tenant-a",
        project_id="proj-bad",
        name="bad-template",
        content="{{ missing_variable }}",
        channel="sms",
        notification_type="pre_trip_reminder",
        is_active=True,
        stage="pre_trip",
        time_slot="morning",
        scene="normal",
    )

    asyncio.run(
        scheduler.check_and_send_notifications_for_slot(
            "morning", now=datetime(2026, 5, 10, 7, 30, tzinfo=UTC)
        )
    )

    assert sms.call_count == 1
    assert sms.calls[0]["customer_id"] == "13800138000"


def test_role_recipients_route_each_role_to_its_configured_channel() -> None:
    trip = _trip(start_offset_days=0, status="in_progress")
    trip["guests"] = []
    trip["role_recipients"] = {
        "manager": {"channel": "sms", "address": "13800000001"},
        "concierge": {"channel": "sms", "address": "13800000002"},
        "driver": {
            "channel": "wechat_work_group",
            "address": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=driver",
        },
    }
    scheduler, sms, wechat, _ = _build_scheduler([trip])

    asyncio.run(
        scheduler.check_and_send_notifications_for_slot(
            "morning", now=datetime(2026, 5, 10, 7, 30, tzinfo=UTC)
        )
    )

    assert {call["customer_id"] for call in sms.calls} == {
        "13800000001",
        "13800000002",
    }
    assert len(wechat.calls) == 1
    assert wechat.calls[0]["customer_id"].startswith("staff:driver:")
    assert wechat.calls[0]["provider_context"]["webhook_url"].endswith("key=driver")
    assert wechat.calls[0]["provider_context"]["role"] == "driver"


def test_configured_role_recipients_do_not_fall_back_to_the_group() -> None:
    trip = _trip(start_offset_days=0, status="in_progress")
    trip["guests"] = []
    trip["webhook_url"] = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=trip"
    trip["role_recipients"] = {
        "manager": {"channel": "sms", "address": "13800000001"},
    }
    scheduler, sms, wechat, _ = _build_scheduler([trip])

    asyncio.run(
        scheduler.check_and_send_notifications_for_slot(
            "morning", now=datetime(2026, 5, 10, 7, 30, tzinfo=UTC)
        )
    )

    assert sms.call_count == 1
    assert sms.calls[0]["customer_id"] == "13800000001"
    assert wechat.call_count == 0


def test_post_trip_end_day_sends_farewell_template() -> None:
    trip = _trip(start_offset_days=-2, status="completed", end_offset_days=0)
    scheduler, sms, _, _ = _build_scheduler([trip])
    scheduler.ctx.template_service.create_notification_template(
        tenant_id="tenant-a",
        project_id="proj-1",
        name="行后欢送",
        content="【欢送】{{customer_name}} 行程结束",
        channel="sms",
        notification_type="farewell",
        is_active=True,
        stage="post_trip",
        time_slot="morning",
        scene="normal",
    )

    asyncio.run(
        scheduler.check_and_send_notifications_for_slot(
            "morning", now=datetime(2026, 5, 10, 7, 30, tzinfo=UTC)
        )
    )

    assert sms.call_count == 1
    assert "欢送" in sms.calls[0]["content"]


def test_weather_warning_scene_uses_weather_template() -> None:
    from app.modules.integration.weather_provider import WeatherInfo

    scheduler, sms, _, _ = _build_scheduler(
        [_trip(start_offset_days=3)],
        weather=FakeWeatherProvider(
            weather=WeatherInfo(
                destination="阿勒泰",
                condition="暴雪",
                temperature=-20.0,
                warning_level="orange",
                alert_title="暴雪橙色预警",
            )
        ),
    )
    scheduler.ctx.template_service.create_notification_template(
        tenant_id="tenant-a",
        project_id="proj-1",
        name="天气预警",
        content="WEATHER {{customer_name}} {{alert_title}}",
        channel="sms",
        notification_type="risk_alert",
        is_active=True,
        stage="pre_trip",
        time_slot="morning",
        scene="weather_alert",
    )

    asyncio.run(
        scheduler.check_and_send_notifications_for_slot(
            "morning", now=datetime(2026, 5, 10, 7, 30, tzinfo=UTC)
        )
    )

    assert sms.call_count == 1
    assert sms.calls[0]["content"].startswith("WEATHER")


def test_invalid_trip_dates_are_skipped_without_crashing() -> None:
    trip = _trip(start_offset_days=3)
    trip["start_date"] = "not-a-date"
    trip["end_date"] = "also-bad"
    scheduler, sms, _, _ = _build_scheduler([trip])

    asyncio.run(
        scheduler.check_and_send_notifications_for_slot(
            "morning", now=datetime(2026, 5, 10, 7, 30, tzinfo=UTC)
        )
    )

    assert sms.call_count == 0


def test_invalid_cron_expression_falls_back_to_default_hour() -> None:
    from app.services.scheduler_service import _parse_cron

    assert _parse_cron("not a cron", 7) == (0, 7)
    assert _parse_cron("15 8 * * *", 7) == (15, 8)
