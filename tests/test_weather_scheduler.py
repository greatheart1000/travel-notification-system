from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.modules.integration.persistence import JsonFileStore
from app.modules.integration.weather_provider import QWeatherProvider
from app.services.scheduler_service import AutoNotificationScheduler
from app.services.template_service import TemplateService


class FakeScheduler:
    def __init__(self) -> None:
        self.jobs: list[dict[str, Any]] = []
        self.started = False
        self.stopped = False

    def add_job(self, func, trigger, **kwargs) -> None:  # noqa: ANN001
        self.jobs.append({"func": func, "trigger": trigger, **kwargs})

    def start(self) -> None:
        self.started = True

    def shutdown(self, wait: bool = False) -> None:
        self.stopped = True


class FakeTripRepository:
    def __init__(self, trips: list[dict[str, Any]]) -> None:
        self._trips = trips

    def list(self) -> list[dict[str, Any]]:
        return list(self._trips)


class FakeNotificationService:
    def __init__(self) -> None:
        self.dispatched = []

    def dispatch(self, task):  # noqa: ANN001
        self.dispatched.append(task)
        task.status = task.status.SENT
        return {"ok": True, "task": task}


class FakeAuditService:
    def __init__(self) -> None:
        self.logs: list[dict[str, Any]] = []

    def record(self, operator_id: str, action: str, target: str, detail: dict[str, Any]) -> None:
        self.logs.append(
            {
                "operator_id": operator_id,
                "action": action,
                "target": target,
                "detail": detail,
            }
        )


class FakeIdempotencyStore:
    def __init__(self) -> None:
        self.keys: set[str] = set()

    def is_processed(self, key: str) -> bool:
        return key in self.keys

    def mark(self, key: str) -> None:
        self.keys.add(key)


class FakeProjectConfigRepository:
    def __init__(self, payload: dict[str, Any] | None = None) -> None:
        self.payload = payload or {}

    def get(self, project_id: str, *, tenant_id: str) -> dict[str, Any] | None:
        if not self.payload:
            return None
        if (
            self.payload.get("project_id") == project_id
            and self.payload.get("tenant_id") == tenant_id
        ):
            return dict(self.payload)
        return None


@dataclass(slots=True)
class FakeCtx:
    trip_repository: FakeTripRepository
    template_service: TemplateService
    notification_service: FakeNotificationService
    audit_service: FakeAuditService
    idempotency_store: FakeIdempotencyStore
    weather_provider: Any
    project_notification_config_repository: Any | None = None
    notification_tasks: dict[str, Any] = field(default_factory=dict)


def test_qweather_provider_builds_weather_summary_from_geo_now_hourly_and_alerts() -> None:
    calls: list[tuple[str, dict[str, str]]] = []

    def fake_transport(
        path: str, params: dict[str, str], headers: dict[str, str]
    ) -> dict[str, Any]:
        calls.append((path, params))
        assert headers["X-QW-Api-Key"] == "test-key"

        if path == "/geo/v2/city/lookup":
            assert params["location"] == "乌鲁木齐"
            return {
                "location": [
                    {"id": "101130101", "name": "乌鲁木齐", "lat": "43.82", "lon": "87.62"},
                ]
            }
        if path == "/v7/weather/now":
            assert params["location"] == "101130101"
            return {"now": {"text": "小雨", "temp": "12"}}
        if path == "/v7/weather/24h":
            return {"hourly": [{"fxTime": "2026-04-21T12:00+09:00", "temp": "9", "text": "阵雨"}]}
        if path == "/weatheralert/v1/current/43.82/87.62":
            return {"warning": [{"title": "暴雨橙色预警"}]}
        raise AssertionError(path)

    provider = QWeatherProvider(
        api_host="https://api.example.com",
        api_key="test-key",
        transport=fake_transport,
    )

    info = provider.get_weather("乌鲁木齐")

    assert info.destination == "乌鲁木齐"
    assert info.condition == "小雨"
    assert info.temperature == 12.0
    assert info.warning_level == "orange"
    assert info.alert_title == "暴雨橙色预警"
    assert info.location_id == "101130101"
    assert len(info.hourly_forecast) == 1
    assert [item[0] for item in calls] == [
        "/geo/v2/city/lookup",
        "/v7/weather/now",
        "/v7/weather/24h",
        "/weatheralert/v1/current/43.82/87.62",
    ]


def test_template_service_prefers_project_specific_weather_alert_template(tmp_path: Path) -> None:
    service = TemplateService(store=JsonFileStore(base_dir=tmp_path))
    fallback = service.create_notification_template(
        tenant_id="tenant-a",
        project_id="",
        name="租户默认晨间天气提醒",
        content="默认模板 {{ customer_name }}",
        channel="sms",
        notification_type="risk_alert",
        is_active=True,
        stage="in_trip",
        time_slot="morning",
        scene="weather_alert",
        sms_sign_name="默认签名",
        provider_template_code="SMS_DEFAULT",
    )
    exact = service.create_notification_template(
        tenant_id="tenant-a",
        project_id="proj-xinjiang",
        name="新疆项目晨间天气预警",
        content="项目模板 {{ customer_name }} {{ alert_title }}",
        channel="sms",
        notification_type="risk_alert",
        is_active=True,
        stage="in_trip",
        time_slot="morning",
        scene="weather_alert",
        sms_sign_name="新疆团",
        provider_template_code="SMS_XJ_ALERT",
    )

    selected = service.pick_notification_template(
        tenant_id="tenant-a",
        project_id="proj-xinjiang",
        stage="in_trip",
        time_slot="morning",
        scene="weather_alert",
        channel="sms",
    )

    assert selected is not None
    assert selected.id == exact.id
    assert selected.id != fallback.id
    assert selected.provider_template_code == "SMS_XJ_ALERT"
    assert selected.sms_sign_name == "新疆团"


def test_auto_notification_scheduler_registers_three_slot_cron_jobs(tmp_path: Path) -> None:
    fake_scheduler = FakeScheduler()
    ctx = FakeCtx(
        trip_repository=FakeTripRepository([]),
        template_service=TemplateService(store=JsonFileStore(base_dir=tmp_path)),
        notification_service=FakeNotificationService(),
        audit_service=FakeAuditService(),
        idempotency_store=FakeIdempotencyStore(),
        weather_provider=None,
    )

    AutoNotificationScheduler(ctx, scheduler=fake_scheduler)

    assert [job["id"] for job in fake_scheduler.jobs] == [
        "notification_morning",
        "notification_noon",
        "notification_evening",
    ]
    assert all(job["trigger"] == "cron" for job in fake_scheduler.jobs)


def test_auto_notification_scheduler_dispatches_project_specific_weather_alert_message(
    tmp_path: Path,
) -> None:
    template_service = TemplateService(store=JsonFileStore(base_dir=tmp_path))
    template_service.create_notification_template(
        tenant_id="tenant-a",
        project_id="proj-xinjiang",
        name="新疆项目晨间天气预警",
        content="【{{ project_name }}】{{ customer_name }}，{{ alert_title }}，{{ weather_text }}",
        channel="sms",
        notification_type="risk_alert",
        is_active=True,
        stage="in_trip",
        time_slot="morning",
        scene="weather_alert",
        sms_sign_name="新疆团",
        provider_template_code="SMS_XJ_ALERT",
    )

    trip = {
        "id": "trip-1",
        "tenant_id": "tenant-a",
        "team_id": "TEAM-1",
        "project_id": "proj-xinjiang",
        "project_name": "新疆阿勒泰团",
        "destination": "乌鲁木齐",
        "status": "in_progress",
        "start_date": "2026-04-20",
        "end_date": "2026-04-23",
        "guests": [{"name": "张三", "phone": "13800138000"}],
        "qweather_location_id": "101130101",
        "qweather_lat": "43.82",
        "qweather_lon": "87.62",
    }

    class StubWeatherProvider:
        def get_weather(
            self,
            destination: str,
            location_context: dict[str, Any] | None = None,
        ) -> object:
            from app.modules.integration.weather_provider import WeatherInfo

            assert destination == "乌鲁木齐"
            assert location_context is not None
            return WeatherInfo(
                destination="乌鲁木齐",
                condition="暴雨",
                temperature=8.0,
                warning_level="red",
                alert_title="暴雨红色预警",
                location_id="101130101",
                hourly_forecast=[{"fxTime": "2026-04-21T08:00:00+08:00", "text": "暴雨"}],
            )

    notification_service = FakeNotificationService()
    audit_service = FakeAuditService()
    ctx = FakeCtx(
        trip_repository=FakeTripRepository([trip]),
        template_service=template_service,
        notification_service=notification_service,
        audit_service=audit_service,
        idempotency_store=FakeIdempotencyStore(),
        weather_provider=StubWeatherProvider(),
    )
    scheduler = AutoNotificationScheduler(ctx, scheduler=FakeScheduler())

    asyncio.run(
        scheduler.check_and_send_notifications_for_slot(
            "morning",
            now=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
        )
    )

    assert len(notification_service.dispatched) == 1
    task = notification_service.dispatched[0]
    assert task.project_id == "proj-xinjiang"
    assert task.notification_type.value == "risk_alert"
    assert "暴雨红色预警" in task.rendered_content
    assert "新疆阿勒泰团" in task.rendered_content
    assert task.provider_context["sms_sign_name"] == "新疆团"
    assert task.provider_context["provider_template_code"] == "SMS_XJ_ALERT"
    assert audit_service.logs[0]["action"] == "auto_notification_dispatched"
    assert audit_service.logs[0]["detail"]["scene"] == "weather_alert"


def test_auto_notification_scheduler_falls_back_to_project_config_for_sms_metadata(
    tmp_path: Path,
) -> None:
    template_service = TemplateService(store=JsonFileStore(base_dir=tmp_path))
    template_service.create_notification_template(
        tenant_id="tenant-a",
        project_id="proj-xinjiang",
        name="新疆项目晨间常规提醒",
        content="【{{ project_name }}】{{ customer_name }}，{{ weather_text }}",
        channel="sms",
        notification_type="daily_reminder",
        is_active=True,
        stage="in_trip",
        time_slot="morning",
        scene="normal",
    )
    trip = {
        "id": "trip-2",
        "tenant_id": "tenant-a",
        "team_id": "TEAM-2",
        "project_id": "proj-xinjiang",
        "project_name": "新疆阿勒泰团",
        "destination": "乌鲁木齐",
        "status": "in_progress",
        "start_date": "2026-04-20",
        "end_date": "2026-04-23",
        "guests": [{"name": "李四", "phone": "13900139000"}],
    }

    class StubWeatherProvider:
        def get_weather(
            self,
            destination: str,
            location_context: dict[str, Any] | None = None,
        ) -> object:
            from app.modules.integration.weather_provider import WeatherInfo

            return WeatherInfo(destination=destination, condition="晴", temperature=18.0)

    project_config_repository = FakeProjectConfigRepository(
        {
            "tenant_id": "tenant-a",
            "project_id": "proj-xinjiang",
            "sms_sign_name": "新疆团默认签名",
            "sms_template_code_normal": "SMS_XJ_NORMAL",
            "sms_template_code_weather_alert": "SMS_XJ_ALERT",
            "weather_alert_thresholds": {"warning_levels": ["orange", "red"]},
        }
    )
    notification_service = FakeNotificationService()
    ctx = FakeCtx(
        trip_repository=FakeTripRepository([trip]),
        template_service=template_service,
        notification_service=notification_service,
        audit_service=FakeAuditService(),
        idempotency_store=FakeIdempotencyStore(),
        weather_provider=StubWeatherProvider(),
        project_notification_config_repository=project_config_repository,
    )
    scheduler = AutoNotificationScheduler(ctx, scheduler=FakeScheduler())

    asyncio.run(
        scheduler.check_and_send_notifications_for_slot(
            "morning",
            now=datetime(2026, 4, 21, 8, 0, tzinfo=UTC),
        )
    )

    assert len(notification_service.dispatched) == 1
    task = notification_service.dispatched[0]
    assert task.provider_context["sms_sign_name"] == "新疆团默认签名"
    assert task.provider_context["provider_template_code"] == "SMS_XJ_NORMAL"
