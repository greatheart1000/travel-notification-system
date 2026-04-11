from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.core.entities import Channel, UserPreference


@dataclass(slots=True)
class UserPreferenceService:
    preferences: dict[str, UserPreference] = field(default_factory=dict)

    def set_preference(
        self, user_id: str, channels: list[Channel], quiet_hours: tuple[int, int]
    ) -> UserPreference:
        pref = UserPreference(user_id=user_id, channels=channels, quiet_hours=quiet_hours)
        self.preferences[user_id] = pref
        return pref

    def get_preference(self, user_id: str) -> UserPreference:
        return self.preferences.get(user_id, UserPreference(user_id=user_id))

    def is_quiet_time(self, user_id: str, now: datetime) -> bool:
        pref = self.get_preference(user_id)
        start, end = pref.quiet_hours
        hour = now.hour
        if start <= end:
            return start <= hour < end
        return hour >= start or hour < end
