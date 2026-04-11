from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.core.entities import Trip


@dataclass(slots=True)
class TripService:
    trips: dict[str, Trip] = field(default_factory=dict)

    def create_trip(
        self, trip_id: str, user_id: str, destination: str, starts_at: datetime
    ) -> Trip:
        trip = Trip(trip_id=trip_id, user_id=user_id, destination=destination, starts_at=starts_at)
        self.trips[trip_id] = trip
        return trip

    def update_trip_status(self, trip_id: str, status: str) -> Trip:
        trip = self.trips[trip_id]
        trip.status = status
        return trip
