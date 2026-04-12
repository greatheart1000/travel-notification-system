from __future__ import annotations

import importlib
import json
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from threading import RLock
from typing import Any

DEFAULT_DB_DIR = "/tmp/travel-notification-system"
DEFAULT_MYSQL_HOST = "127.0.0.1"
DEFAULT_MYSQL_PORT = 3306
DEFAULT_MYSQL_USER = "root"
DEFAULT_MYSQL_PASSWORD = "123456"
DEFAULT_MYSQL_DATABASE = "travel_notification_system"
DEFAULT_TENANT_ID = "tenant-a"


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    return str(value)


def _to_iso_datetime(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value or "")


def _to_iso_date(value: Any) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return str(value or "")


def _to_mysql_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    raw = str(value or "").strip()
    if not raw:
        return datetime.utcnow()
    raw = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
        return parsed.replace(tzinfo=None)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return datetime.utcnow()


def _to_mysql_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    raw = str(value or "").strip()
    if not raw:
        return datetime.utcnow().date()
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return datetime.utcnow().date()


def _normalize_trip_status(raw: Any) -> str:
    value = str(raw or "planned").strip().lower()
    mapping = {
        "planned": "planned",
        "计划中": "planned",
        "in_progress": "in_progress",
        "active": "in_progress",
        "进行中": "in_progress",
        "completed": "completed",
        "已完成": "completed",
        "cancelled": "cancelled",
        "已取消": "cancelled",
    }
    return mapping.get(value, "planned")


def _normalize_rule_stage(raw: Any) -> str:
    value = str(raw or "pre_trip").strip().lower()
    mapping = {
        "pre_trip": "pre_trip",
        "before_departure": "pre_trip",
        "before": "pre_trip",
        "行前": "pre_trip",
        "in_trip": "in_trip",
        "on_trip": "in_trip",
        "during": "in_trip",
        "行中": "in_trip",
        "post_trip": "post_trip",
        "after_trip": "post_trip",
        "after": "post_trip",
        "行后": "post_trip",
    }
    return mapping.get(value, "pre_trip")


def _normalize_rule_time_slot(raw: Any) -> str:
    value = str(raw or "all_day").strip().lower()
    mapping = {
        "morning": "morning",
        "am": "morning",
        "afternoon": "afternoon",
        "pm": "afternoon",
        "evening": "evening",
        "night": "night",
        "all_day": "all_day",
        "any": "all_day",
        "anytime": "all_day",
    }
    return mapping.get(value, "all_day")


def _normalize_rule_scene(raw: Any) -> str:
    value = str(raw or "normal").strip().lower()
    mapping = {
        "normal": "normal",
        "default": "normal",
        "weather": "weather_alert",
        "weather_alert": "weather_alert",
        "delay": "delay",
        "flight_delay": "delay",
        "complaint": "complaint",
        "manual": "manual",
    }
    return mapping.get(value, "normal")


def _normalize_channel(raw: Any, *, allow_email: bool = True) -> str:
    value = str(raw or "sms").strip().lower()
    mapping = {
        "sms": "sms",
        "短信": "sms",
        "wechat_work_group": "wechat_work_group",
        "wechat": "wechat_work_group",
        "wechat_work": "wechat_work_group",
        "企业微信": "wechat_work_group",
        "email": "email",
        "邮件": "email",
    }
    normalized = mapping.get(value, "sms")
    if not allow_email and normalized == "email":
        return "sms"
    return normalized


def _normalize_notification_type(raw: Any) -> str:
    value = str(raw or "daily_reminder").strip().lower()
    mapping = {
        "pre_trip_reminder": "pre_trip_reminder",
        "daily_reminder": "daily_reminder",
        "risk_alert": "risk_alert",
        "satisfaction": "satisfaction",
        "farewell": "farewell",
        "complaint_escalation": "risk_alert",
        "booking_success": "pre_trip_reminder",
    }
    return mapping.get(value, "daily_reminder")


def _normalize_task_status(raw: Any) -> str:
    value = str(raw or "pending").strip().lower()
    allowed = {"pending", "sent", "failed", "manual_intervention", "skipped"}
    if value in allowed:
        return value
    return "pending"


def _normalize_tenant_id(raw: Any) -> str:
    tenant_id = str(raw or "").strip()
    return tenant_id or DEFAULT_TENANT_ID


@dataclass(slots=True)
class JsonFileStore:
    """Storage facade: MySQL by default, JSON files as explicit fallback."""

    base_dir: str | Path | None = None
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)
    _mysql_enabled: bool = field(default=False, init=False, repr=False)
    _mysql_config: dict[str, Any] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        backend = os.getenv("TRAVEL_NOTIFICATION_PERSISTENCE_BACKEND", "mysql").strip().lower()
        use_json_backend = self.base_dir is not None or backend == "json"

        if use_json_backend:
            self._init_json_backend()
            return

        self._init_mysql_backend()

    def _init_json_backend(self) -> None:
        if self.base_dir is None:
            self.base_dir = os.getenv("TRAVEL_NOTIFICATION_DB_DIR", DEFAULT_DB_DIR)
        self.base_dir = Path(self.base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _init_mysql_backend(self) -> None:
        host = os.getenv("TRAVEL_NOTIFICATION_MYSQL_HOST", DEFAULT_MYSQL_HOST).strip()
        user = os.getenv("TRAVEL_NOTIFICATION_MYSQL_USER", DEFAULT_MYSQL_USER).strip()
        password = os.getenv("TRAVEL_NOTIFICATION_MYSQL_PASSWORD", DEFAULT_MYSQL_PASSWORD)
        database = os.getenv("TRAVEL_NOTIFICATION_MYSQL_DATABASE", DEFAULT_MYSQL_DATABASE).strip()
        port_raw = os.getenv("TRAVEL_NOTIFICATION_MYSQL_PORT", str(DEFAULT_MYSQL_PORT)).strip()

        self._mysql_config = {
            "host": host,
            "user": user,
            "password": password,
            "database": database,
            "port": int(port_raw or str(DEFAULT_MYSQL_PORT)),
            "charset": "utf8mb4",
            "autocommit": True,
        }
        self._mysql_enabled = True
        self.base_dir = f"mysql://{user}@{host}:{self._mysql_config['port']}/{database}"
        self._ensure_mysql_schema()

    def _mysql_connector(self) -> Any:
        return importlib.import_module("pymysql")

    def _mysql_connect(self) -> Any:
        connector = self._mysql_connector()
        return connector.connect(
            **self._mysql_config,
            cursorclass=connector.cursors.DictCursor,
        )

    def _ensure_mysql_schema(self) -> None:
        if not self._mysql_enabled:
            return
        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:

                def has_table(table_name: str) -> bool:
                    cursor.execute(
                        """
                        SELECT COUNT(*) AS cnt
                        FROM information_schema.TABLES
                        WHERE TABLE_SCHEMA = DATABASE()
                          AND TABLE_NAME = %s
                        """,
                        (table_name,),
                    )
                    return int((cursor.fetchone() or {}).get("cnt", 0)) > 0

                def has_column(table_name: str, column_name: str) -> bool:
                    cursor.execute(
                        """
                        SELECT COUNT(*) AS cnt
                        FROM information_schema.COLUMNS
                        WHERE TABLE_SCHEMA = DATABASE()
                          AND TABLE_NAME = %s
                          AND COLUMN_NAME = %s
                        """,
                        (table_name, column_name),
                    )
                    return int((cursor.fetchone() or {}).get("cnt", 0)) > 0

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS t_collection_store (
                        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                        collection_name VARCHAR(128) NOT NULL,
                        item_key VARCHAR(128) NOT NULL,
                        payload JSON NOT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        PRIMARY KEY (id),
                        UNIQUE KEY uk_collection_item (collection_name, item_key),
                        KEY idx_collection_updated (collection_name, updated_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
                    """
                )

                if has_table("t_notification_task"):
                    if not has_column("t_notification_task", "team_id"):
                        cursor.execute(
                            """
                            ALTER TABLE t_notification_task
                            ADD COLUMN team_id VARCHAR(64) NOT NULL DEFAULT '' AFTER trip_id
                            """
                        )
                    if not has_column("t_notification_task", "tenant_id"):
                        cursor.execute(
                            f"""
                            ALTER TABLE t_notification_task
                            ADD COLUMN tenant_id VARCHAR(64) NOT NULL DEFAULT '{DEFAULT_TENANT_ID}'
                            AFTER customer_id
                            """
                        )
                    cursor.execute(
                        """
                        SELECT IS_NULLABLE AS nullable_flag
                        FROM information_schema.COLUMNS
                        WHERE TABLE_SCHEMA = DATABASE()
                          AND TABLE_NAME = 't_notification_task'
                          AND COLUMN_NAME = 'trip_id'
                        """
                    )
                    trip_nullable = (cursor.fetchone() or {}).get("nullable_flag") == "YES"
                    if not trip_nullable:
                        cursor.execute(
                            """
                            ALTER TABLE t_notification_task
                            MODIFY COLUMN trip_id BIGINT UNSIGNED NULL
                            """
                        )
                    cursor.execute(
                        """
                        UPDATE t_notification_task
                        SET tenant_id = %s
                        WHERE tenant_id IS NULL OR tenant_id = ''
                        """,
                        (DEFAULT_TENANT_ID,),
                    )

                if has_table("t_trip"):
                    if not has_column("t_trip", "tenant_id"):
                        cursor.execute(
                            f"""
                            ALTER TABLE t_trip
                            ADD COLUMN tenant_id VARCHAR(64) NOT NULL DEFAULT '{DEFAULT_TENANT_ID}'
                            AFTER owner_user_id
                            """
                        )
                    cursor.execute(
                        """
                        UPDATE t_trip
                        SET tenant_id = %s
                        WHERE tenant_id IS NULL OR tenant_id = ''
                        """,
                        (DEFAULT_TENANT_ID,),
                    )

                if has_table("t_notification_template"):
                    if not has_column("t_notification_template", "tenant_id"):
                        cursor.execute(
                            f"""
                            ALTER TABLE t_notification_template
                            ADD COLUMN tenant_id VARCHAR(64) NOT NULL DEFAULT '{DEFAULT_TENANT_ID}'
                            AFTER template_name
                            """
                        )
                    cursor.execute(
                        """
                        UPDATE t_notification_template
                        SET tenant_id = %s
                        WHERE tenant_id IS NULL OR tenant_id = ''
                        """,
                        (DEFAULT_TENANT_ID,),
                    )

                if has_table("t_notification_rule"):
                    if not has_column("t_notification_rule", "tenant_id"):
                        cursor.execute(
                            f"""
                            ALTER TABLE t_notification_rule
                            ADD COLUMN tenant_id VARCHAR(64) NOT NULL DEFAULT '{DEFAULT_TENANT_ID}'
                            AFTER rule_name
                            """
                        )
                    cursor.execute(
                        """
                        UPDATE t_notification_rule
                        SET tenant_id = %s
                        WHERE tenant_id IS NULL OR tenant_id = ''
                        """,
                        (DEFAULT_TENANT_ID,),
                    )
        finally:
            connection.close()

    def _collection_path(self, collection: str) -> Path:
        if isinstance(self.base_dir, Path):
            return self.base_dir / f"{collection}.json"
        return Path(DEFAULT_DB_DIR) / f"{collection}.json"

    def read_collection(self, collection: str) -> list[dict[str, Any]]:
        if self._mysql_enabled:
            return self._read_collection_mysql(collection)
        return self._read_collection_json(collection)

    def write_collection(self, collection: str, items: list[dict[str, Any]]) -> None:
        if self._mysql_enabled:
            self._write_collection_mysql(collection, items)
            return
        self._write_collection_json(collection, items)

    def upsert(self, collection: str, item: dict[str, Any], key: str = "id") -> dict[str, Any]:
        if self._mysql_enabled:
            return self._upsert_mysql(collection, item, key)

        items = self.read_collection(collection)
        existing_index = next(
            (idx for idx, row in enumerate(items) if row.get(key) == item.get(key)), None
        )
        if existing_index is None:
            items.append(item)
        else:
            items[existing_index] = item
        self.write_collection(collection, items)
        return item

    def delete(self, collection: str, item_id: str, key: str = "id") -> bool:
        if self._mysql_enabled:
            return self._delete_mysql(collection, item_id, key)

        items = self.read_collection(collection)
        next_items = [row for row in items if row.get(key) != item_id]
        if len(next_items) == len(items):
            return False
        self.write_collection(collection, next_items)
        return True

    def clear_all(self) -> None:
        if self._mysql_enabled:
            self._clear_all_mysql()
            return
        for path in self._collection_path(".").parent.glob("*.json"):
            path.unlink(missing_ok=True)

    def _read_collection_json(self, collection: str) -> list[dict[str, Any]]:
        path = self._collection_path(collection)
        if not path.exists():
            return []
        with self._lock:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return []
        if not isinstance(data, list):
            return []
        return [item for item in data if isinstance(item, dict)]

    def _write_collection_json(self, collection: str, items: list[dict[str, Any]]) -> None:
        path = self._collection_path(collection)
        payload = json.dumps(items, ensure_ascii=False, default=_json_default, indent=2)
        temp_path = path.with_suffix(".tmp")
        with self._lock:
            temp_path.write_text(payload, encoding="utf-8")
            temp_path.replace(path)

    def _read_collection_mysql(self, collection: str) -> list[dict[str, Any]]:
        if collection == "trips":
            return self._read_mysql_trips()
        if collection == "templates":
            return self._read_mysql_templates()
        if collection == "notification_rules":
            return self._read_mysql_notification_rules()
        if collection == "notification_attempts":
            return self._read_mysql_notification_attempts()
        return self._read_mysql_generic_collection(collection)

    def _write_collection_mysql(self, collection: str, items: list[dict[str, Any]]) -> None:
        if collection == "templates":
            self._write_mysql_templates(items)
            return
        if collection == "notification_rules":
            self._write_mysql_notification_rules(items)
            return
        if collection == "notification_attempts":
            self._write_mysql_notification_attempts(items)
            return
        if collection == "trips":
            for item in items:
                self._upsert_mysql_trip(item, key="id")
            return
        self._write_mysql_generic_collection(collection, items)

    def _upsert_mysql(self, collection: str, item: dict[str, Any], key: str) -> dict[str, Any]:
        if collection == "trips":
            self._upsert_mysql_trip(item, key)
            return item
        self._upsert_mysql_generic(collection, item, key)
        return item

    def _delete_mysql(self, collection: str, item_id: str, key: str) -> bool:
        if collection == "trips":
            return self._delete_mysql_trip(item_id)
        if collection == "templates" and key == "id":
            return self._delete_mysql_template(item_id)
        if collection == "notification_rules" and key == "id":
            return self._delete_mysql_rule(item_id)
        return self._delete_mysql_generic(collection, item_id, key)

    def _clear_all_mysql(self) -> None:
        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
                cursor.execute("TRUNCATE TABLE t_notification_attempt")
                cursor.execute("TRUNCATE TABLE t_notification_task")
                cursor.execute("TRUNCATE TABLE t_notification_rule_channel")
                cursor.execute("TRUNCATE TABLE t_notification_rule")
                cursor.execute("TRUNCATE TABLE t_notification_template")
                cursor.execute("TRUNCATE TABLE t_trip")
                cursor.execute("TRUNCATE TABLE t_collection_store")
                cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        finally:
            connection.close()

    def _read_mysql_trips(self) -> list[dict[str, Any]]:
        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT trip_code, destination, team_id, start_date, end_date,
                           participants, status, owner_user_id, tenant_id, created_at, updated_at
                    FROM t_trip
                    ORDER BY created_at DESC, id DESC
                    """
                )
                rows = cursor.fetchall()
        finally:
            connection.close()

        items: list[dict[str, Any]] = []
        for row in rows:
            team_id = str(row.get("team_id") or "")
            items.append(
                {
                    "id": str(row.get("trip_code") or ""),
                    "destination": str(row.get("destination") or ""),
                    "team": team_id,
                    "team_id": team_id,
                    "start_date": _to_iso_date(row.get("start_date")),
                    "end_date": _to_iso_date(row.get("end_date")),
                    "participants": int(row.get("participants") or 0),
                    "status": _normalize_trip_status(row.get("status")),
                    "user_id": str(row.get("owner_user_id") or ""),
                    "tenant_id": _normalize_tenant_id(row.get("tenant_id")),
                    "created_at": _to_iso_datetime(row.get("created_at")),
                    "updated_at": _to_iso_datetime(row.get("updated_at")),
                }
            )
        return items

    def _upsert_mysql_trip(self, item: dict[str, Any], key: str = "id") -> None:
        trip_code = str(item.get(key) or item.get("id") or "").strip()
        if not trip_code:
            raise ValueError("trip id is required")

        team_id = str(item.get("team_id") or item.get("team") or "").strip()
        created_at = _to_mysql_datetime(item.get("created_at"))
        updated_at = _to_mysql_datetime(item.get("updated_at"))

        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO t_trip
                    (trip_code, destination, team_id, start_date, end_date, participants, status,
                     owner_user_id, tenant_id, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                      destination = VALUES(destination),
                      team_id = VALUES(team_id),
                      start_date = VALUES(start_date),
                      end_date = VALUES(end_date),
                      participants = VALUES(participants),
                      status = VALUES(status),
                      owner_user_id = VALUES(owner_user_id),
                      tenant_id = VALUES(tenant_id),
                      updated_at = VALUES(updated_at)
                    """,
                    (
                        trip_code,
                        str(item.get("destination") or ""),
                        team_id,
                        _to_mysql_date(item.get("start_date")),
                        _to_mysql_date(item.get("end_date")),
                        int(item.get("participants") or 0),
                        _normalize_trip_status(item.get("status")),
                        str(item.get("user_id") or "admin"),
                        _normalize_tenant_id(item.get("tenant_id")),
                        created_at,
                        updated_at,
                    ),
                )
        finally:
            connection.close()

    def _delete_mysql_trip(self, trip_code: str) -> bool:
        connection = self._mysql_connect()
        connection.autocommit(False)
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM t_trip WHERE trip_code = %s", (trip_code,))
                row = cursor.fetchone()
                if row is None:
                    connection.rollback()
                    return False
                trip_pk = int(row["id"])

                cursor.execute(
                    """
                    DELETE a
                    FROM t_notification_attempt AS a
                    JOIN t_notification_task AS t ON t.id = a.task_id
                    WHERE t.trip_id = %s
                    """,
                    (trip_pk,),
                )
                cursor.execute("DELETE FROM t_notification_task WHERE trip_id = %s", (trip_pk,))
                cursor.execute("DELETE FROM t_trip WHERE id = %s", (trip_pk,))
            connection.commit()
            return True
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _read_mysql_templates(self) -> list[dict[str, Any]]:
        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT template_code, template_name, notification_type, channel,
                           tenant_id, content, version, is_active, created_at, updated_at
                    FROM t_notification_template
                    ORDER BY updated_at DESC, id DESC
                    """
                )
                rows = cursor.fetchall()
        finally:
            connection.close()

        items: list[dict[str, Any]] = []
        seen_codes: set[str] = set()
        for row in rows:
            template_code = str(row.get("template_code") or "").strip()
            if not template_code or template_code in seen_codes:
                continue
            seen_codes.add(template_code)
            items.append(
                {
                    "id": template_code,
                    "name": str(row.get("template_name") or ""),
                    "version": int(row.get("version") or 1),
                    "tenant_id": _normalize_tenant_id(row.get("tenant_id")),
                    "notification_type": _normalize_notification_type(row.get("notification_type")),
                    "channel": _normalize_channel(row.get("channel")),
                    "content": str(row.get("content") or ""),
                    "is_active": bool(row.get("is_active")),
                    "created_at": _to_iso_datetime(row.get("created_at")),
                    "updated_at": _to_iso_datetime(row.get("updated_at")),
                }
            )
        return items

    def _write_mysql_templates(self, items: list[dict[str, Any]]) -> None:
        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:
                for raw in items:
                    template_code = str(raw.get("id") or "").strip()
                    if not template_code:
                        continue
                    cursor.execute(
                        """
                        INSERT INTO t_notification_template
                        (template_code, template_name, tenant_id, notification_type, channel, content,
                         version, is_active, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                          template_name = VALUES(template_name),
                          tenant_id = VALUES(tenant_id),
                          notification_type = VALUES(notification_type),
                          channel = VALUES(channel),
                          content = VALUES(content),
                          version = VALUES(version),
                          is_active = VALUES(is_active),
                          updated_at = VALUES(updated_at)
                        """,
                        (
                            template_code,
                            str(raw.get("name") or ""),
                            _normalize_tenant_id(raw.get("tenant_id")),
                            _normalize_notification_type(raw.get("notification_type")),
                            _normalize_channel(raw.get("channel")),
                            str(raw.get("content") or ""),
                            max(int(raw.get("version") or 1), 1),
                            1 if bool(raw.get("is_active", True)) else 0,
                            _to_mysql_datetime(raw.get("created_at")),
                            _to_mysql_datetime(raw.get("updated_at")),
                        ),
                    )
        finally:
            connection.close()

    def _delete_mysql_template(self, template_code: str) -> bool:
        connection = self._mysql_connect()
        connection.autocommit(False)
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM t_notification_template WHERE template_code = %s",
                    (template_code,),
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
                    (template_code,),
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

    def _read_mysql_notification_rules(self) -> list[dict[str, Any]]:
        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT r.id, r.rule_code, r.rule_name, r.tenant_id, r.stage, r.time_slot, r.scene,
                           r.priority, r.enabled, r.conditions_json,
                           r.created_at, r.updated_at,
                           t.template_code
                    FROM t_notification_rule AS r
                    LEFT JOIN t_notification_template AS t ON t.id = r.template_id
                    ORDER BY r.priority ASC, r.updated_at DESC, r.id DESC
                    """
                )
                rules = cursor.fetchall()

                cursor.execute(
                    """
                    SELECT c.rule_id, c.channel, c.sort_order
                    FROM t_notification_rule_channel AS c
                    ORDER BY c.rule_id ASC, c.sort_order ASC
                    """
                )
                channels_rows = cursor.fetchall()
        finally:
            connection.close()

        channels_by_rule: dict[int, list[str]] = {}
        for row in channels_rows:
            rule_id = int(row.get("rule_id") or 0)
            channels_by_rule.setdefault(rule_id, []).append(_normalize_channel(row.get("channel")))

        items: list[dict[str, Any]] = []
        for row in rules:
            rule_id = int(row.get("id") or 0)
            conditions_raw = row.get("conditions_json")
            if isinstance(conditions_raw, str):
                try:
                    conditions = json.loads(conditions_raw)
                except json.JSONDecodeError:
                    conditions = {}
            elif isinstance(conditions_raw, dict):
                conditions = conditions_raw
            else:
                conditions = {}

            items.append(
                {
                    "id": str(row.get("rule_code") or ""),
                    "name": str(row.get("rule_name") or ""),
                    "tenant_id": _normalize_tenant_id(row.get("tenant_id")),
                    "stage": _normalize_rule_stage(row.get("stage")),
                    "time_slot": _normalize_rule_time_slot(row.get("time_slot")),
                    "scene": _normalize_rule_scene(row.get("scene")),
                    "channels": channels_by_rule.get(rule_id, []),
                    "template_id": str(row.get("template_code") or "") or None,
                    "enabled": bool(row.get("enabled")),
                    "priority": int(row.get("priority") or 100),
                    "conditions": conditions if isinstance(conditions, dict) else {},
                    "created_at": _to_iso_datetime(row.get("created_at")),
                    "updated_at": _to_iso_datetime(row.get("updated_at")),
                }
            )
        return items

    def _write_mysql_notification_rules(self, items: list[dict[str, Any]]) -> None:
        connection = self._mysql_connect()
        connection.autocommit(False)
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT rule_code FROM t_notification_rule")
                existing_codes = {str(row["rule_code"]) for row in cursor.fetchall()}
                desired_codes = {
                    str(item.get("id") or "").strip()
                    for item in items
                    if str(item.get("id") or "").strip()
                }
                codes_to_delete = [code for code in existing_codes if code not in desired_codes]
                if codes_to_delete:
                    placeholders = ", ".join(["%s"] * len(codes_to_delete))
                    cursor.execute(
                        f"DELETE FROM t_notification_rule WHERE rule_code IN ({placeholders})",
                        tuple(codes_to_delete),
                    )

                cursor.execute(
                    "SELECT id, template_code FROM t_notification_template ORDER BY id ASC"
                )
                template_rows = cursor.fetchall()
                template_id_by_code = {
                    str(row.get("template_code") or ""): int(row.get("id") or 0)
                    for row in template_rows
                }
                default_template_id = int(template_rows[0]["id"]) if template_rows else None
                if default_template_id is None:
                    raise RuntimeError("No templates in MySQL, cannot persist notification rules")

                for item in items:
                    rule_code = str(item.get("id") or "").strip()
                    if not rule_code:
                        continue
                    template_code = str(item.get("template_id") or "").strip()
                    template_fk = template_id_by_code.get(template_code, default_template_id)
                    conditions = item.get("conditions")
                    if not isinstance(conditions, dict):
                        conditions = {}

                    cursor.execute(
                        """
                        INSERT INTO t_notification_rule
                        (rule_code, rule_name, tenant_id, stage, time_slot, scene, template_id, priority,
                         enabled, conditions_json, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                          rule_name = VALUES(rule_name),
                          tenant_id = VALUES(tenant_id),
                          stage = VALUES(stage),
                          time_slot = VALUES(time_slot),
                          scene = VALUES(scene),
                          template_id = VALUES(template_id),
                          priority = VALUES(priority),
                          enabled = VALUES(enabled),
                          conditions_json = VALUES(conditions_json),
                          updated_at = VALUES(updated_at),
                          id = LAST_INSERT_ID(id)
                        """,
                        (
                            rule_code,
                            str(item.get("name") or ""),
                            _normalize_tenant_id(item.get("tenant_id")),
                            _normalize_rule_stage(item.get("stage")),
                            _normalize_rule_time_slot(item.get("time_slot")),
                            _normalize_rule_scene(item.get("scene")),
                            template_fk,
                            int(item.get("priority") or 100),
                            1 if bool(item.get("enabled", True)) else 0,
                            json.dumps(conditions, ensure_ascii=False),
                            _to_mysql_datetime(item.get("created_at")),
                            _to_mysql_datetime(item.get("updated_at")),
                        ),
                    )
                    rule_pk = int(cursor.lastrowid)

                    cursor.execute(
                        "DELETE FROM t_notification_rule_channel WHERE rule_id = %s", (rule_pk,)
                    )
                    channels = item.get("channels")
                    if not isinstance(channels, list):
                        channels = []
                    normalized_channels: list[str] = []
                    for channel in channels:
                        normalized = _normalize_channel(channel)
                        if normalized in normalized_channels:
                            continue
                        normalized_channels.append(normalized)
                    for index, channel in enumerate(normalized_channels, start=1):
                        cursor.execute(
                            """
                            INSERT INTO t_notification_rule_channel (rule_id, channel, sort_order)
                            VALUES (%s, %s, %s)
                            """,
                            (rule_pk, channel, index),
                        )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _delete_mysql_rule(self, rule_code: str) -> bool:
        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:
                affected = cursor.execute(
                    "DELETE FROM t_notification_rule WHERE rule_code = %s", (rule_code,)
                )
            return affected > 0
        finally:
            connection.close()

    def _ensure_trip_exists(
        self,
        cursor: Any,
        *,
        trip_code: str,
        tenant_id: str,
        team_id: str,
        customer_id: str,
        attempted_at: datetime,
    ) -> int:
        cursor.execute("SELECT id FROM t_trip WHERE trip_code = %s", (trip_code,))
        row = cursor.fetchone()
        if row is not None:
            return int(row["id"])

        cursor.execute(
            """
            INSERT INTO t_trip
            (trip_code, destination, team_id, start_date, end_date, participants, status,
             owner_user_id, tenant_id, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                trip_code,
                "未命名行程",
                team_id,
                attempted_at.date(),
                attempted_at.date(),
                0,
                "planned",
                customer_id or "admin",
                _normalize_tenant_id(tenant_id),
                attempted_at,
                attempted_at,
            ),
        )
        return int(cursor.lastrowid)

    def _upsert_task_from_attempt_item(self, cursor: Any, item: dict[str, Any]) -> int:
        task_code = str(item.get("task_id") or item.get("attempt_id") or "").strip()
        if not task_code:
            task_code = f"task-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"

        attempted_at = _to_mysql_datetime(item.get("attempted_at"))
        trip_code = str(item.get("trip_id") or "").strip()
        tenant_id = _normalize_tenant_id(item.get("tenant_id"))
        team_id = str(item.get("team_id") or "").strip()
        customer_id = str(item.get("customer_id") or "").strip()
        trip_fk: int | None = None

        if trip_code:
            trip_fk = self._ensure_trip_exists(
                cursor,
                trip_code=trip_code,
                tenant_id=tenant_id,
                team_id=team_id,
                customer_id=customer_id,
                attempted_at=attempted_at,
            )

        cursor.execute(
            """
            INSERT INTO t_notification_task
            (task_code, trip_id, team_id, customer_id, tenant_id, notification_type,
             primary_channel, fallback_channel, rendered_content,
             idempotency_key, status, retry_count, max_retry,
             manual_intervention_required, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
              trip_id = VALUES(trip_id),
              team_id = VALUES(team_id),
              customer_id = VALUES(customer_id),
              tenant_id = VALUES(tenant_id),
              primary_channel = VALUES(primary_channel),
              status = VALUES(status),
              retry_count = GREATEST(retry_count, VALUES(retry_count)),
              manual_intervention_required = VALUES(manual_intervention_required),
              updated_at = VALUES(updated_at),
              id = LAST_INSERT_ID(id)
            """,
            (
                task_code,
                trip_fk,
                team_id,
                customer_id,
                tenant_id,
                _normalize_notification_type(item.get("notification_type")),
                _normalize_channel(item.get("channel"), allow_email=True),
                None,
                "",
                f"history:{task_code}",
                _normalize_task_status(item.get("status")),
                max(int(item.get("attempt_no") or 1), 0),
                2,
                1 if _normalize_task_status(item.get("status")) == "manual_intervention" else 0,
                attempted_at,
                attempted_at,
            ),
        )
        return int(cursor.lastrowid)

    def _write_mysql_notification_attempts(self, items: list[dict[str, Any]]) -> None:
        if not items:
            return

        ordered_items = sorted(
            items,
            key=lambda item: (
                str(item.get("attempted_at") or ""),
                str(item.get("task_id") or ""),
                int(item.get("attempt_no") or 0),
            ),
        )

        connection = self._mysql_connect()
        connection.autocommit(False)
        try:
            with connection.cursor() as cursor:
                for item in ordered_items:
                    task_pk = self._upsert_task_from_attempt_item(cursor, item)
                    cursor.execute(
                        """
                        INSERT INTO t_notification_attempt
                        (task_id, attempt_no, channel, ok, reason, provider_message, latency_ms, attempted_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                          channel = VALUES(channel),
                          ok = VALUES(ok),
                          reason = VALUES(reason),
                          provider_message = VALUES(provider_message),
                          latency_ms = VALUES(latency_ms),
                          attempted_at = VALUES(attempted_at)
                        """,
                        (
                            task_pk,
                            max(int(item.get("attempt_no") or 1), 1),
                            _normalize_channel(item.get("channel"), allow_email=True),
                            1 if bool(item.get("ok", False)) else 0,
                            str(item.get("reason") or ""),
                            str(item.get("provider_message") or ""),
                            max(int(item.get("latency_ms") or 0), 0),
                            _to_mysql_datetime(item.get("attempted_at")),
                        ),
                    )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _read_mysql_notification_attempts(self) -> list[dict[str, Any]]:
        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT a.id AS attempt_id,
                           a.attempt_no,
                           a.channel,
                           a.ok,
                           a.reason,
                           a.provider_message,
                           a.latency_ms,
                           a.attempted_at,
                           t.task_code,
                           t.customer_id,
                           t.tenant_id,
                           t.status,
                           t.team_id,
                           tr.trip_code,
                           tr.team_id AS trip_team_id
                    FROM t_notification_attempt AS a
                    JOIN t_notification_task AS t ON t.id = a.task_id
                    LEFT JOIN t_trip AS tr ON tr.id = t.trip_id
                    ORDER BY a.attempted_at DESC, a.id DESC
                    """
                )
                rows = cursor.fetchall()
        finally:
            connection.close()

        items: list[dict[str, Any]] = []
        for row in rows:
            team_id = str(row.get("team_id") or row.get("trip_team_id") or "")
            items.append(
                {
                    "attempt_id": str(row.get("attempt_id") or ""),
                    "task_id": str(row.get("task_code") or ""),
                    "trip_id": str(row.get("trip_code") or ""),
                    "tenant_id": _normalize_tenant_id(row.get("tenant_id")),
                    "team_id": team_id,
                    "customer_id": str(row.get("customer_id") or ""),
                    "attempt_no": int(row.get("attempt_no") or 1),
                    "channel": _normalize_channel(row.get("channel"), allow_email=True),
                    "ok": bool(row.get("ok")),
                    "reason": str(row.get("reason") or ""),
                    "provider_message": str(row.get("provider_message") or ""),
                    "latency_ms": int(row.get("latency_ms") or 0),
                    "status": _normalize_task_status(row.get("status")),
                    "attempted_at": _to_iso_datetime(row.get("attempted_at")),
                }
            )
        return items

    def _read_mysql_generic_collection(self, collection: str) -> list[dict[str, Any]]:
        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT payload
                    FROM t_collection_store
                    WHERE collection_name = %s
                    ORDER BY updated_at DESC, id DESC
                    """,
                    (collection,),
                )
                rows = cursor.fetchall()
        finally:
            connection.close()

        items: list[dict[str, Any]] = []
        for row in rows:
            payload = row.get("payload")
            if isinstance(payload, str):
                try:
                    parsed = json.loads(payload)
                except json.JSONDecodeError:
                    continue
            else:
                parsed = payload
            if isinstance(parsed, dict):
                items.append(parsed)
        return items

    def _collection_item_key(self, item: dict[str, Any], index: int, preferred: str = "id") -> str:
        candidate = str(item.get(preferred) or "").strip()
        if candidate:
            return candidate
        for fallback in ("user_id", "feedback_id", "event_id", "task_id", "attempt_id"):
            value = str(item.get(fallback) or "").strip()
            if value:
                return value
        return f"row-{index}"

    def _write_mysql_generic_collection(self, collection: str, items: list[dict[str, Any]]) -> None:
        connection = self._mysql_connect()
        connection.autocommit(False)
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM t_collection_store WHERE collection_name = %s", (collection,)
                )
                for index, item in enumerate(items):
                    cursor.execute(
                        """
                        INSERT INTO t_collection_store (collection_name, item_key, payload)
                        VALUES (%s, %s, %s)
                        """,
                        (
                            collection,
                            self._collection_item_key(item, index),
                            json.dumps(item, ensure_ascii=False, default=_json_default),
                        ),
                    )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _upsert_mysql_generic(self, collection: str, item: dict[str, Any], key: str) -> None:
        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO t_collection_store (collection_name, item_key, payload)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE payload = VALUES(payload)
                    """,
                    (
                        collection,
                        self._collection_item_key(item, 0, preferred=key),
                        json.dumps(item, ensure_ascii=False, default=_json_default),
                    ),
                )
        finally:
            connection.close()

    def _delete_mysql_generic(self, collection: str, item_id: str, key: str) -> bool:
        if key != "id":
            rows = self._read_mysql_generic_collection(collection)
            filtered = [row for row in rows if str(row.get(key)) != str(item_id)]
            if len(filtered) == len(rows):
                return False
            self._write_mysql_generic_collection(collection, filtered)
            return True

        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:
                affected = cursor.execute(
                    """
                    DELETE FROM t_collection_store
                    WHERE collection_name = %s AND item_key = %s
                    """,
                    (collection, str(item_id)),
                )
            return affected > 0
        finally:
            connection.close()


@dataclass(slots=True)
class TripRepository:
    store: JsonFileStore
    collection: str = "trips"

    def list(self) -> list[dict[str, Any]]:
        return self.store.read_collection(self.collection)

    def get(self, trip_id: str) -> dict[str, Any] | None:
        for item in self.list():
            if item.get("id") == trip_id:
                return item
        return None

    def create(self, trip: dict[str, Any]) -> dict[str, Any]:
        return self.store.upsert(self.collection, trip)

    def update(self, trip_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        current = self.get(trip_id)
        if current is None:
            return None
        current.update(patch)
        current["updated_at"] = datetime.utcnow().isoformat()
        self.store.upsert(self.collection, current)
        return current

    def delete(self, trip_id: str) -> bool:
        return self.store.delete(self.collection, trip_id)
