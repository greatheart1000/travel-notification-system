from __future__ import annotations

import importlib
import os
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

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
    mysql_enabled: bool = field(default=False, init=False)
    mysql_config: dict[str, Any] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self._init_mysql_config()
        if self.mysql_enabled:
            for row in self._read_mysql_templates():
                template = self._from_mysql_row(row)
                self.notification_templates[template.id] = template
            return
        if self.store is None:
            return
        for row in self.store.read_collection(self.collection):
            template = self._from_payload(row)
            self.notification_templates[template.id] = template

    def _init_mysql_config(self) -> None:
        host = os.getenv("TRAVEL_NOTIFICATION_MYSQL_HOST", "").strip()
        user = os.getenv("TRAVEL_NOTIFICATION_MYSQL_USER", "").strip()
        password = os.getenv("TRAVEL_NOTIFICATION_MYSQL_PASSWORD", "").strip()
        database = os.getenv("TRAVEL_NOTIFICATION_MYSQL_DATABASE", "").strip()
        port_raw = os.getenv("TRAVEL_NOTIFICATION_MYSQL_PORT", "3306").strip()
        if not host or not user or not password or not database:
            return
        self.mysql_enabled = True
        self.mysql_config = {
            "host": host,
            "user": user,
            "password": password,
            "database": database,
            "port": int(port_raw or "3306"),
            "charset": "utf8mb4",
            "autocommit": True,
        }

    def _mysql_connector(self) -> Any:
        module = importlib.import_module("pymysql")
        return module

    def _read_mysql_templates(self) -> list[dict[str, Any]]:
        connector = self._mysql_connector()
        connection = connector.connect(**self.mysql_config)
        try:
            with connection.cursor(connector.cursors.DictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT t.template_code, t.template_name, t.tenant_id, t.project_id,
                           t.notification_type, t.channel, t.stage, t.time_slot, t.scene,
                           t.sms_sign_name, t.provider_template_code,
                           t.content, t.version, t.is_active
                    FROM t_notification_template AS t
                    INNER JOIN (
                        SELECT template_code, MAX(version) AS max_version
                        FROM t_notification_template
                        GROUP BY template_code
                    ) AS latest
                      ON latest.template_code = t.template_code
                     AND latest.max_version = t.version
                    ORDER BY t.updated_at DESC, t.id DESC
                    """
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        finally:
            connection.close()

    def _from_mysql_row(self, row: dict[str, Any]) -> NotificationTemplate:
        template = NotificationTemplate(
            id=str(row.get("template_code", "")),
            tenant_id=str(row.get("tenant_id", "")),
            project_id=str(row.get("project_id", "")),
            name=str(row.get("template_name", "")),
            version=int(row.get("version", 1)),
            notification_type=self._parse_notification_type(
                str(row.get("notification_type", "daily_reminder"))
            ),
            channel=self._parse_channel(str(row.get("channel", "sms"))),
            stage=str(row.get("stage", "")),
            time_slot=str(row.get("time_slot", "")),
            scene=str(row.get("scene", "")),
            sms_sign_name=str(row.get("sms_sign_name", "")),
            provider_template_code=str(row.get("provider_template_code", "")),
            content=str(row.get("content", "")),
            is_active=bool(row.get("is_active", True)),
        )
        return template

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

    def _to_mysql_notification_type(self, value: NotificationType) -> str:
        mapping = {
            NotificationType.PRE_TRIP_REMINDER: "pre_trip_reminder",
            NotificationType.DAILY_REMINDER: "daily_reminder",
            NotificationType.RISK_ALERT: "risk_alert",
            NotificationType.SATISFACTION: "satisfaction",
            NotificationType.FAREWELL: "farewell",
            NotificationType.COMPLAINT_ESCALATION: "risk_alert",
            NotificationType.BOOKING_SUCCESS: "pre_trip_reminder",
        }
        return mapping.get(value, "daily_reminder")

    def _to_payload(self, template: NotificationTemplate) -> dict[str, object]:
        return {
            "id": template.id,
            "tenant_id": template.tenant_id,
            "project_id": template.project_id,
            "name": template.name,
            "version": template.version,
            "notification_type": template.notification_type.value,
            "channel": template.channel.value,
            "stage": template.stage,
            "time_slot": template.time_slot,
            "scene": template.scene,
            "sms_sign_name": template.sms_sign_name,
            "provider_template_code": template.provider_template_code,
            "content": template.content,
            "is_active": template.is_active,
            "created_at": template.created_at.isoformat(),
            "updated_at": template.updated_at.isoformat(),
        }

    def _from_payload(self, row: dict[str, object]) -> NotificationTemplate:
        return NotificationTemplate(
            id=str(row.get("id", "")),
            tenant_id=str(row.get("tenant_id", "")),
            project_id=str(row.get("project_id", "")),
            name=str(row.get("name", "")),
            version=int(row.get("version", 1)),
            notification_type=self._parse_notification_type(
                str(row.get("notification_type", "daily_reminder"))
            ),
            channel=self._parse_channel(str(row.get("channel", "sms"))),
            stage=str(row.get("stage", "")),
            time_slot=str(row.get("time_slot", "")),
            scene=str(row.get("scene", "")),
            sms_sign_name=str(row.get("sms_sign_name", "")),
            provider_template_code=str(row.get("provider_template_code", "")),
            content=str(row.get("content", "")),
            is_active=bool(row.get("is_active", True)),
        )

    def _flush(self) -> None:
        if self.mysql_enabled:
            self._flush_mysql()
            return
        if self.store is None:
            return
        payload = [self._to_payload(item) for item in self.notification_templates.values()]
        self.store.write_collection(self.collection, payload)

    def _flush_mysql(self) -> None:
        connector = self._mysql_connector()
        connection = connector.connect(**self.mysql_config)
        try:
            with connection.cursor() as cursor:
                for template in self.notification_templates.values():
                    cursor.execute(
                        """
                        INSERT INTO t_notification_template
                        (template_code, template_name, tenant_id, project_id, notification_type, channel,
                         stage, time_slot, scene, sms_sign_name, provider_template_code, content, version, is_active)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                          template_name = VALUES(template_name),
                          tenant_id = VALUES(tenant_id),
                          project_id = VALUES(project_id),
                          notification_type = VALUES(notification_type),
                          channel = VALUES(channel),
                          stage = VALUES(stage),
                          time_slot = VALUES(time_slot),
                          scene = VALUES(scene),
                          sms_sign_name = VALUES(sms_sign_name),
                          provider_template_code = VALUES(provider_template_code),
                          content = VALUES(content),
                          is_active = VALUES(is_active),
                          version = VALUES(version)
                        """,
                        (
                            template.id,
                            template.name,
                            template.tenant_id,
                            template.project_id,
                            self._to_mysql_notification_type(template.notification_type),
                            template.channel.value,
                            template.stage,
                            template.time_slot,
                            template.scene,
                            template.sms_sign_name,
                            template.provider_template_code,
                            template.content,
                            template.version,
                            1 if template.is_active else 0,
                        ),
                    )
        finally:
            connection.close()

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

    def render_notification(self, template: NotificationTemplate, variables: dict[str, Any]) -> str:
        """Render ``{{ variable }}`` placeholders and fail fast on missing fields."""
        placeholders = set(re.findall(r"{{\s*([a-zA-Z0-9_]+)\s*}}", template.content))
        missing = sorted(name for name in placeholders if name not in variables)
        if missing:
            raise ValueError(f"missing_template_variables: {','.join(missing)}")

        def replace(match: re.Match[str]) -> str:
            key = match.group(1)
            return str(variables.get(key, ""))

        return re.sub(r"{{\s*([a-zA-Z0-9_]+)\s*}}", replace, template.content)

    def list_notification_templates(
        self, tenant_id: str | None = None
    ) -> list[NotificationTemplate]:
        if not tenant_id:
            return list(self.notification_templates.values())
        return [
            item for item in self.notification_templates.values() if item.tenant_id == tenant_id
        ]

    def get_notification_template(
        self, template_id: str, tenant_id: str | None = None
    ) -> NotificationTemplate | None:
        template = self.notification_templates.get(template_id)
        if template is None:
            return None
        if tenant_id and template.tenant_id != tenant_id:
            return None
        return template

    def ensure_default_template(self, tenant_id: str = "") -> NotificationTemplate:
        existing_sms = [
            item
            for item in self.list_notification_templates(tenant_id=tenant_id)
            if item.is_active and item.channel == Channel.SMS
        ]
        if existing_sms:
            return sorted(existing_sms, key=lambda item: item.updated_at, reverse=True)[0]

        # 预置高质量的默认行程提醒模板
        content = (
            "【行程提醒】尊敬的{{customer_name}}，您前往{{destination}}的行程即将在{{trip_date}}开始。\n"
            "🚗 交通提示：{{flight_info}}\n"
            "🏞️ 沿途亮点：{{highlight}}\n"
            "⛅ 天气提醒：{{climate}}\n"
            "👕 穿衣指南：{{dress_code}}\n"
            "祝您旅途愉快！"
        )
        return self.create_notification_template(
            tenant_id=tenant_id,
            name="精选默认行程提醒",
            content=content,
            channel="sms",
            notification_type="daily_reminder",
            is_active=True,
        )

    def create_notification_template(
        self,
        tenant_id: str,
        name: str,
        content: str,
        channel: str,
        notification_type: str,
        is_active: bool,
        project_id: str = "",
        stage: str = "",
        time_slot: str = "",
        scene: str = "",
        sms_sign_name: str = "",
        provider_template_code: str = "",
    ) -> NotificationTemplate:
        template = NotificationTemplate(
            tenant_id=tenant_id,
            project_id=project_id,
            name=name,
            content=content,
            channel=self._parse_channel(channel),
            notification_type=self._parse_notification_type(notification_type),
            stage=stage,
            time_slot=time_slot,
            scene=scene,
            sms_sign_name=sms_sign_name,
            provider_template_code=provider_template_code,
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
        project_id: str | None = None,
        stage: str | None = None,
        time_slot: str | None = None,
        scene: str | None = None,
        sms_sign_name: str | None = None,
        provider_template_code: str | None = None,
    ) -> NotificationTemplate | None:
        template = self.notification_templates.get(template_id)
        if template is None:
            return None
        if project_id is not None:
            template.project_id = project_id
        if name is not None:
            template.name = name
        if content is not None:
            template.content = content
        if channel is not None:
            template.channel = self._parse_channel(channel)
        if notification_type is not None:
            template.notification_type = self._parse_notification_type(notification_type)
        if stage is not None:
            template.stage = stage
        if time_slot is not None:
            template.time_slot = time_slot
        if scene is not None:
            template.scene = scene
        if sms_sign_name is not None:
            template.sms_sign_name = sms_sign_name
        if provider_template_code is not None:
            template.provider_template_code = provider_template_code
        if is_active is not None:
            template.is_active = is_active
        template.updated_at = datetime.now(tz=UTC)
        self.notification_templates[template_id] = template
        self._flush()
        return template

    def pick_notification_template(
        self,
        *,
        tenant_id: str,
        project_id: str,
        stage: str,
        time_slot: str,
        scene: str,
        channel: str,
    ) -> NotificationTemplate | None:
        channel_value = self._parse_channel(channel)
        candidates = [
            template
            for template in self.notification_templates.values()
            if template.tenant_id == tenant_id
            and template.is_active
            and template.channel == channel_value
        ]
        if not candidates:
            return None

        ranked = sorted(
            candidates,
            key=lambda item: (
                1 if item.project_id == project_id and item.project_id else 0,
                1 if item.stage == stage and item.stage else 0,
                1 if item.time_slot == time_slot and item.time_slot else 0,
                1 if item.scene == scene and item.scene else 0,
                item.updated_at.isoformat(),
            ),
            reverse=True,
        )
        selected = ranked[0]
        score = (
            (1 if selected.project_id == project_id and selected.project_id else 0)
            + (1 if selected.stage == stage and selected.stage else 0)
            + (1 if selected.time_slot == time_slot and selected.time_slot else 0)
            + (1 if selected.scene == scene and selected.scene else 0)
        )
        if score == 0:
            return None
        return selected

    def delete_notification_template(self, template_id: str) -> bool:
        if template_id not in self.notification_templates:
            return False
        deleted = False
        if self.store is not None:
            deleted = self.store.delete(self.collection, template_id, key="id")
        elif self.mysql_enabled:
            deleted = self._delete_mysql_template_with_rebind(template_id)
        else:
            deleted = True

        if not deleted:
            return False

        del self.notification_templates[template_id]
        self._flush()
        return True

    def _delete_mysql_template_with_rebind(self, template_id: str) -> bool:
        connector = self._mysql_connector()
        connection = connector.connect(**self.mysql_config)
        connection.autocommit(False)
        try:
            with connection.cursor(connector.cursors.DictCursor) as cursor:
                cursor.execute(
                    "SELECT id FROM t_notification_template WHERE template_code = %s",
                    (template_id,),
                )
                target = cursor.fetchone()
                if target is None:
                    connection.rollback()
                    return False

                cursor.execute(
                    """
                    SELECT id FROM t_notification_template
                    WHERE template_code <> %s
                    ORDER BY updated_at DESC, id DESC
                    LIMIT 1
                    """,
                    (template_id,),
                )
                replacement = cursor.fetchone()
                if replacement is None:
                    connection.rollback()
                    return False

                cursor.execute(
                    "UPDATE t_notification_rule SET template_id = %s WHERE template_id = %s",
                    (int(replacement["id"]), int(target["id"])),
                )
                cursor.execute(
                    "DELETE FROM t_notification_template WHERE id = %s",
                    (int(target["id"]),),
                )
            connection.commit()
            return True
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
