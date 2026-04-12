from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.core.entities import EventName
from app.core.entities import Template as RuleTemplate
from app.core.models import Channel, NotificationType
from app.modules.integration.persistence import JsonFileStore
from app.modules.notification.models import NotificationTemplate

UTC = UTC


@dataclass(slots=True)
class TemplateService:
    templates: list[RuleTemplate] = field(default_factory=list)
    notification_templates: dict[str, NotificationTemplate] = field(default_factory=dict)
    store: JsonFileStore | None = None
    collection: str = "templates"

    def __post_init__(self) -> None:
        if self.store is None:
            return
        for row in self.store.read_collection(self.collection):
            template = self._from_payload(row)
            self.notification_templates[template.id] = template

    def _parse_channel(self, value: str | Channel) -> Channel:
        if isinstance(value, Channel):
            return value
        raw = str(value).strip().lower()
        matched = next((item for item in Channel if item.value == raw), None)
        return matched or Channel.SMS

    def _parse_notification_type(self, value: str | NotificationType) -> NotificationType:
        if isinstance(value, NotificationType):
            return value
        raw = str(value).strip().lower()
        matched = next((item for item in NotificationType if item.value == raw), None)
        return matched or NotificationType.DAILY_REMINDER

    def _to_payload(self, template: NotificationTemplate) -> dict[str, object]:
        return {
            "id": template.id,
            "name": template.name,
            "version": template.version,
            "notification_type": template.notification_type.value,
            "channel": template.channel.value,
            "content": template.content,
            "is_active": template.is_active,
            "created_at": template.created_at.isoformat(),
            "updated_at": template.updated_at.isoformat(),
        }

    def _from_payload(self, row: dict[str, object]) -> NotificationTemplate:
        return NotificationTemplate(
            id=str(row.get("id", "")),
            name=str(row.get("name", "")),
            version=int(row.get("version", 1)),
            notification_type=self._parse_notification_type(
                str(row.get("notification_type", "daily_reminder"))
            ),
            channel=self._parse_channel(str(row.get("channel", "sms"))),
            content=str(row.get("content", "")),
            is_active=bool(row.get("is_active", True)),
        )

    def _flush(self) -> None:
        if self.store is None:
            return
        payload = [self._to_payload(item) for item in self.notification_templates.values()]
        self.store.write_collection(self.collection, payload)

    def upsert_template(self, template: RuleTemplate) -> None:
        self.templates = [
            t
            for t in self.templates
            if not (
                t.event_name == template.event_name
                and t.locale == template.locale
                and t.version == template.version
                and t.ab_bucket == template.ab_bucket
            )
        ] + [template]

    def pick_template(
        self, event_name: EventName, locale: str, ab_bucket: str = "A"
    ) -> RuleTemplate:
        enabled = [
            t
            for t in self.templates
            if t.event_name == event_name
            and t.locale == locale
            and t.enabled
            and t.ab_bucket == ab_bucket
        ]
        if not enabled:
            enabled = [
                t
                for t in self.templates
                if t.event_name == event_name and t.locale == "zh" and t.enabled
            ]
        if not enabled:
            raise ValueError(f"template missing for {event_name}")
        return sorted(enabled, key=lambda x: x.version, reverse=True)[0]

    def render(self, template: RuleTemplate, variables: dict[str, str]) -> str:
        content = template.content
        for key, value in variables.items():
            content = content.replace(f"{{{{{key}}}}}", value)
        return content

    def render_notification(self, template: NotificationTemplate, variables: dict[str, str]) -> str:
        content = template.content
        for key, value in variables.items():
            content = content.replace(f"{{{{{key}}}}}", str(value))
        return content

    def list_notification_templates(self) -> list[NotificationTemplate]:
        return list(self.notification_templates.values())

    def get_notification_template(self, template_id: str) -> NotificationTemplate | None:
        return self.notification_templates.get(template_id)

    def ensure_default_template(self) -> NotificationTemplate:
        existing = self.list_notification_templates()
        if existing:
            return existing[0]
        return self.create_notification_template(
            name="默认行程提醒",
            content="{{customer_name}}，您的{{destination}}行程即将开始，请准时集合。",
            channel="sms",
            notification_type="daily_reminder",
            is_active=True,
        )

    def create_notification_template(
        self,
        name: str,
        content: str,
        channel: str,
        notification_type: str,
        is_active: bool,
    ) -> NotificationTemplate:
        template = NotificationTemplate(
            name=name,
            content=content,
            channel=self._parse_channel(channel),
            notification_type=self._parse_notification_type(notification_type),
            is_active=is_active,
        )
        self.notification_templates[template.id] = template
        self._flush()
        return template

    def update_notification_template(
        self,
        template_id: str,
        *,
        name: str | None = None,
        content: str | None = None,
        channel: str | None = None,
        notification_type: str | None = None,
        is_active: bool | None = None,
    ) -> NotificationTemplate | None:
        template = self.notification_templates.get(template_id)
        if template is None:
            return None
        if name is not None:
            template.name = name
        if content is not None:
            template.content = content
        if channel is not None:
            template.channel = self._parse_channel(channel)
        if notification_type is not None:
            template.notification_type = self._parse_notification_type(notification_type)
        if is_active is not None:
            template.is_active = is_active
        template.updated_at = datetime.now(tz=UTC)
        self.notification_templates[template_id] = template
        self._flush()
        return template

    def delete_notification_template(self, template_id: str) -> bool:
        if template_id not in self.notification_templates:
            return False
        del self.notification_templates[template_id]
        self._flush()
        return True
