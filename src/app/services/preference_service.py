from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.core.entities import Channel, UserPreference
from app.modules.integration.persistence import JsonFileStore


@dataclass(slots=True)
class UserPreferenceService:
    preferences: dict[str, UserPreference] = field(default_factory=dict)
    advanced_settings: dict[str, dict[str, object]] = field(default_factory=dict)
    store: JsonFileStore | None = None
    collection: str = "preferences"

    def __post_init__(self) -> None:
        if self.store is None:
            return
        for row in self.store.read_collection(self.collection):
            user_id = str(row.get("user_id", "")).strip()
            if not user_id:
                continue
            channels = self._parse_channels(row.get("channels", []))
            quiet_hours = self._parse_quiet_hours(row.get("quiet_hours", (23, 7)))
            allow_marketing = bool(row.get("allow_marketing", True))
            self.preferences[user_id] = UserPreference(
                user_id=user_id,
                channels=channels,
                quiet_hours=quiet_hours,
                allow_marketing=allow_marketing,
            )
            self.advanced_settings[user_id] = self._normalize_advanced_settings(row)

    def _parse_channels(self, values: list[str] | list[Channel]) -> list[Channel]:
        channels: list[Channel] = []
        for value in values:
            if isinstance(value, Channel):
                channels.append(value)
                continue
            raw = str(value).strip().lower()
            matched = next((item for item in Channel if item.value == raw), None)
            if matched is not None:
                channels.append(matched)
        return channels or [Channel.EMAIL, Channel.PUSH]

    def _parse_hour(self, value: object, fallback: int) -> int:
        if isinstance(value, int):
            hour = value
        else:
            raw = str(value).strip()
            if ":" in raw:
                raw = raw.split(":", 1)[0]
            if not raw.isdigit():
                return fallback
            hour = int(raw)
        if not (0 <= hour <= 23):
            return fallback
        return hour

    def _parse_quiet_hours(
        self, quiet_hours: tuple[int, int] | list[int] | dict[str, Any]
    ) -> tuple[int, int]:
        if isinstance(quiet_hours, dict):
            start = self._parse_hour(quiet_hours.get("start", 23), 23)
            end = self._parse_hour(quiet_hours.get("end", 7), 7)
            return (start, end)
        if len(quiet_hours) != 2:
            return (23, 7)
        start = self._parse_hour(quiet_hours[0], 23)
        end = self._parse_hour(quiet_hours[1], 7)
        if not (0 <= start <= 23 and 0 <= end <= 23):
            return (23, 7)
        return (start, end)

    def _normalize_advanced_settings(
        self, payload: dict[str, Any] | None = None
    ) -> dict[str, object]:
        payload = payload or {}
        return {
            "max_notifications_per_hour": int(payload.get("max_notifications_per_hour", 5)),
            "auto_escalation": bool(payload.get("auto_escalation", True)),
            "aggregate_notifications": bool(payload.get("aggregate_notifications", True)),
        }

    def _settings_for_user(self, user_id: str) -> dict[str, object]:
        return self.advanced_settings.get(user_id, self._normalize_advanced_settings())

    def _flush(self) -> None:
        if self.store is None:
            return
        payload = [self.to_payload(pref) for pref in self.preferences.values()]
        self.store.write_collection(self.collection, payload)

    def to_payload(self, preference: UserPreference) -> dict[str, object]:
        advanced = self._settings_for_user(preference.user_id)
        return {
            "user_id": preference.user_id,
            "channels": [channel.value for channel in preference.channels],
            "quiet_hours": [preference.quiet_hours[0], preference.quiet_hours[1]],
            "max_notifications_per_hour": advanced["max_notifications_per_hour"],
            "auto_escalation": advanced["auto_escalation"],
            "aggregate_notifications": advanced["aggregate_notifications"],
            "allow_marketing": preference.allow_marketing,
        }

    def set_preference(
        self, user_id: str, channels: list[Channel], quiet_hours: tuple[int, int]
    ) -> UserPreference:
        pref = UserPreference(user_id=user_id, channels=channels, quiet_hours=quiet_hours)
        self.preferences[user_id] = pref
        self.advanced_settings[user_id] = self._settings_for_user(user_id)
        self._flush()
        return pref

    def set_preference_from_payload(
        self,
        user_id: str,
        channels: list[str],
        quiet_hours: list[int] | dict[str, Any],
        allow_marketing: bool | None = None,
        max_notifications_per_hour: int | None = None,
        auto_escalation: bool | None = None,
        aggregate_notifications: bool | None = None,
    ) -> UserPreference:
        current = self.get_preference(user_id)
        pref = UserPreference(
            user_id=user_id,
            channels=self._parse_channels(channels),
            quiet_hours=self._parse_quiet_hours(quiet_hours),
            allow_marketing=current.allow_marketing if allow_marketing is None else allow_marketing,
        )
        self.preferences[user_id] = pref
        advanced = self._settings_for_user(user_id)
        if max_notifications_per_hour is not None:
            advanced["max_notifications_per_hour"] = int(max_notifications_per_hour)
        if auto_escalation is not None:
            advanced["auto_escalation"] = bool(auto_escalation)
        if aggregate_notifications is not None:
            advanced["aggregate_notifications"] = bool(aggregate_notifications)
        self.advanced_settings[user_id] = advanced
        self._flush()
        return pref

    def get_preference(self, user_id: str) -> UserPreference:
        return self.preferences.get(user_id, UserPreference(user_id=user_id))

    def get_preference_payload(self, user_id: str) -> dict[str, object]:
        return self.to_payload(self.get_preference(user_id))

    def is_quiet_time(self, user_id: str, now: datetime) -> bool:
        pref = self.get_preference(user_id)
        start, end = pref.quiet_hours
        hour = now.hour
        if start <= end:
            return start <= hour < end
        return hour >= start or hour < end
