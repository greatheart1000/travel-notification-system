from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.core.entities import Channel, DomainEvent, EventName, Template
from app.core.event_bus import InMemoryEventBus
from app.services.preference_service import UserPreferenceService
from app.services.rule_engine import NotificationRuleEngine, Rule
from app.services.template_service import TemplateService
from app.services.trip_service import TripService


@dataclass(slots=True)
class ManagementBFF:
    trip_service: TripService
    preference_service: UserPreferenceService
    template_service: TemplateService
    rule_engine: NotificationRuleEngine
    event_bus: InMemoryEventBus

    def create_trip(self, trip_id: str, user_id: str, destination: str, starts_at: datetime) -> dict:
        trip = self.trip_service.create_trip(trip_id, user_id, destination, starts_at)
        return {"trip_id": trip.trip_id, "status": trip.status}

    def update_preference(self, user_id: str, channels: list[Channel], quiet_hours: tuple[int, int]) -> dict:
        pref = self.preference_service.set_preference(user_id, channels, quiet_hours)
        return {"user_id": pref.user_id, "channels": [c.value for c in pref.channels]}

    def upsert_template(
        self,
        template_id: str,
        event_name: EventName,
        locale: str,
        version: int,
        content: str,
        ab_bucket: str = "A",
        enabled: bool = True,
    ) -> None:
        self.template_service.upsert_template(
            Template(
                template_id=template_id,
                event_name=event_name,
                locale=locale,
                version=version,
                content=content,
                ab_bucket=ab_bucket,
                enabled=enabled,
            )
        )

    def upsert_rule(self, event_name: EventName, priority: int, channels: list[Channel], max_per_hour: int) -> None:
        self.rule_engine.upsert_rule(
            Rule(
                event_name=event_name,
                priority=priority,
                channels=channels,
                max_per_hour=max_per_hour,
            )
        )

    def ingest_event(self, event: DomainEvent) -> None:
        self.event_bus.push_outbox(event)
