from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.api.bff import ManagementBFF
from app.core.entities import Channel, DeliveryStatus, DomainEvent, EventName
from app.core.event_bus import InMemoryEventBus
from app.providers.adapters import EmailProvider, PushProvider, SmsProvider
from app.services.dispatch_service import DispatchService
from app.services.preference_service import UserPreferenceService
from app.services.rule_engine import NotificationRuleEngine
from app.services.template_service import TemplateService
from app.services.trip_service import TripService


def build_app(fail_push_once: bool = False) -> tuple[ManagementBFF, DispatchService, InMemoryEventBus]:
    trip_service = TripService()
    preference_service = UserPreferenceService()
    template_service = TemplateService()
    rule_engine = NotificationRuleEngine()
    event_bus = InMemoryEventBus()
    dispatch_service = DispatchService(
        providers={
            Channel.EMAIL: EmailProvider(),
            Channel.PUSH: PushProvider(fail_first=fail_push_once),
            Channel.SMS: SmsProvider(),
        }
    )

    bff = ManagementBFF(
        trip_service=trip_service,
        preference_service=preference_service,
        template_service=template_service,
        rule_engine=rule_engine,
        event_bus=event_bus,
    )

    def handle_event(event: DomainEvent) -> None:
        now = datetime.now(timezone.utc)
        if preference_service.is_quiet_time(event.user_id, now):
            return
        rule = rule_engine.match(event)
        if not rule_engine.allow_send(event.user_id, event.name, now):
            return

        pref = preference_service.get_preference(event.user_id)
        channels = [c for c in pref.channels if c in rule.channels] or rule.channels
        template = template_service.pick_template(event.name, locale="zh")
        content = template_service.render(template, {"trip_id": event.trip_id, "event": event.name.value})
        dispatch_service.send_with_fallback(event, content, channels)

    for event_name in EventName:
        event_bus.subscribe(event_name.value, handle_event)

    return bff, dispatch_service, event_bus


def bootstrap_demo() -> dict:
    bff, dispatch_service, bus = build_app(fail_push_once=True)

    bff.create_trip("T-100", "U-100", "Xinjiang", datetime(2026, 6, 1, tzinfo=timezone.utc))
    bff.update_preference("U-100", [Channel.PUSH, Channel.EMAIL], (1, 2))
    bff.upsert_rule(EventName.TRIP_CREATED, priority=1, channels=[Channel.PUSH, Channel.EMAIL], max_per_hour=2)
    bff.upsert_template(
        template_id="tpl-zh-v1",
        event_name=EventName.TRIP_CREATED,
        locale="zh",
        version=1,
        content="行程 {{trip_id}} 已创建，事件 {{event}}",
        ab_bucket="A",
    )

    event = DomainEvent(
        event_id=str(uuid4()),
        name=EventName.TRIP_CREATED,
        trip_id="T-100",
        user_id="U-100",
    )
    bff.ingest_event(event)
    published = bus.flush_outbox()
    latest = dispatch_service.records[-1]

    return {
        "published": published,
        "status": latest.status == DeliveryStatus.SUCCESS,
        "channel": latest.channel.value,
        "attempt": latest.attempt,
    }


if __name__ == "__main__":
    print(bootstrap_demo())
