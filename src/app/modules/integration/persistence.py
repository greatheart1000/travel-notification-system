from __future__ import annotations

import fcntl
import importlib
import json
import os
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
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


def _utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _to_mysql_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    raw = str(value or "").strip()
    if not raw:
        return _utc_now_naive()
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
    return _utc_now_naive()


def _to_mysql_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    raw = str(value or "").strip()
    if not raw:
        return _utc_now_naive().date()
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return _utc_now_naive().date()


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


def _parse_json_object(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if raw in (None, ""):
        return {}
    if isinstance(raw, bytes | bytearray):
        raw = raw.decode("utf-8", "ignore")
    try:
        parsed = json.loads(str(raw))
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


@dataclass(slots=True)
class JsonFileStore:
    """Storage facade: MySQL by default, JSON files as explicit fallback."""

    base_dir: str | Path | None = None
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)
    _mysql_enabled: bool = field(default=False, init=False, repr=False)
    _mysql_config: dict[str, Any] = field(default_factory=dict, init=False, repr=False)
    _indexes: dict[str, dict[str, list[int]]] = field(default_factory=dict, init=False, repr=False)
    _collection_cache: dict[str, list[dict]] = field(default_factory=dict, init=False, repr=False)
    _advisory_held: set[str] = field(default_factory=set, init=False, repr=False)
    _advisory_handles: dict[str, Any] = field(default_factory=dict, init=False, repr=False)

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

    def _build_index(self, collection: str, field: str, items: list[dict]) -> None:
        """为集合的指定字段构建内存索引（O(1) 查找）。"""
        if collection not in self._indexes:
            self._indexes[collection] = {}
        idx: dict[str, list[int]] = {}
        for i, item in enumerate(items):
            val = str(item.get(field, ""))
            idx.setdefault(val, []).append(i)
        self._indexes[collection][field] = idx

    def find_by_index(self, collection: str, field: str, value: str) -> list[dict]:
        """使用索引 O(1) 查找（如果索引存在），否则回退到扫描。"""
        items = self.read_collection(collection)
        if collection in self._indexes and field in self._indexes[collection]:
            indices = self._indexes[collection][field].get(value, [])
            return [items[i] for i in indices if i < len(items)]
        # 回退：扫描 + 自动建索引
        self._build_index(collection, field, items)
        return [item for item in items if str(item.get(field, "")) == value]

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

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS t_project_notification_config (
                        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                        tenant_id VARCHAR(64) NOT NULL DEFAULT 'tenant-a',
                        project_id VARCHAR(64) NOT NULL,
                        project_name VARCHAR(128) NOT NULL DEFAULT '',
                        weather_enabled TINYINT(1) NOT NULL DEFAULT 1,
                        qweather_credential_id VARCHAR(64) NOT NULL DEFAULT '',
                        qweather_location_id VARCHAR(64) NOT NULL DEFAULT '',
                        qweather_lat VARCHAR(32) NOT NULL DEFAULT '',
                        qweather_lon VARCHAR(32) NOT NULL DEFAULT '',
                        weather_alert_threshold_json JSON NULL,
                        sms_provider VARCHAR(32) NOT NULL DEFAULT 'aliyun',
                        sms_sign_name VARCHAR(64) NOT NULL DEFAULT '',
                        sms_template_code_normal VARCHAR(64) NOT NULL DEFAULT '',
                        sms_template_code_weather_alert VARCHAR(64) NOT NULL DEFAULT '',
                        manual_takeover_target VARCHAR(128) NOT NULL DEFAULT '',
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        PRIMARY KEY (id),
                        UNIQUE KEY uk_project_notification_config (tenant_id, project_id),
                        KEY idx_project_name (project_name)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
                    """
                )

                cursor.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS t_trip (
                        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                        trip_code VARCHAR(64) NOT NULL,
                        destination VARCHAR(128) NOT NULL,
                        team_id VARCHAR(64) NOT NULL,
                        start_date DATE NOT NULL,
                        end_date DATE NOT NULL,
                        participants INT UNSIGNED NOT NULL DEFAULT 0,
                        status ENUM('planned','in_progress','completed','cancelled') NOT NULL DEFAULT 'planned',
                        owner_user_id VARCHAR(64) NOT NULL DEFAULT 'admin',
                        tenant_id VARCHAR(64) NOT NULL DEFAULT '{DEFAULT_TENANT_ID}',
                        ext_data JSON NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        PRIMARY KEY (id),
                        UNIQUE KEY uk_trip_code (trip_code),
                        KEY idx_team_id (team_id),
                        KEY idx_status_dates (status, start_date, end_date)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
                    """
                )

                cursor.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS t_notification_template (
                        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                        template_code VARCHAR(64) NOT NULL,
                        template_name VARCHAR(128) NOT NULL,
                        tenant_id VARCHAR(64) NOT NULL DEFAULT '{DEFAULT_TENANT_ID}',
                        project_id VARCHAR(64) NOT NULL DEFAULT '',
                        notification_type ENUM('pre_trip_reminder','daily_reminder','risk_alert','satisfaction','farewell')
                            NOT NULL DEFAULT 'daily_reminder',
                        channel ENUM('sms','wechat_work_group','email') NOT NULL DEFAULT 'sms',
                        stage VARCHAR(32) NOT NULL DEFAULT '',
                        time_slot VARCHAR(32) NOT NULL DEFAULT '',
                        scene VARCHAR(32) NOT NULL DEFAULT '',
                        sms_sign_name VARCHAR(64) NOT NULL DEFAULT '',
                        provider_template_code VARCHAR(64) NOT NULL DEFAULT '',
                        content TEXT NOT NULL,
                        version INT UNSIGNED NOT NULL DEFAULT 1,
                        is_active TINYINT(1) NOT NULL DEFAULT 1,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        PRIMARY KEY (id),
                        UNIQUE KEY uk_template_code_version (template_code, version),
                        KEY idx_template_active (is_active)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
                    """
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
                    if not has_column("t_notification_template", "project_id"):
                        cursor.execute(
                            """
                            ALTER TABLE t_notification_template
                            ADD COLUMN project_id VARCHAR(64) NOT NULL DEFAULT '' AFTER tenant_id
                            """
                        )
                    if not has_column("t_notification_template", "stage"):
                        cursor.execute(
                            """
                            ALTER TABLE t_notification_template
                            ADD COLUMN stage VARCHAR(32) NOT NULL DEFAULT '' AFTER channel
                            """
                        )
                    if not has_column("t_notification_template", "time_slot"):
                        cursor.execute(
                            """
                            ALTER TABLE t_notification_template
                            ADD COLUMN time_slot VARCHAR(32) NOT NULL DEFAULT '' AFTER stage
                            """
                        )
                    if not has_column("t_notification_template", "scene"):
                        cursor.execute(
                            """
                            ALTER TABLE t_notification_template
                            ADD COLUMN scene VARCHAR(32) NOT NULL DEFAULT '' AFTER time_slot
                            """
                        )
                    if not has_column("t_notification_template", "sms_sign_name"):
                        cursor.execute(
                            """
                            ALTER TABLE t_notification_template
                            ADD COLUMN sms_sign_name VARCHAR(64) NOT NULL DEFAULT '' AFTER scene
                            """
                        )
                    if not has_column("t_notification_template", "provider_template_code"):
                        cursor.execute(
                            """
                            ALTER TABLE t_notification_template
                            ADD COLUMN provider_template_code VARCHAR(64) NOT NULL DEFAULT '' AFTER sms_sign_name
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

                cursor.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS t_notification_rule (
                        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                        rule_code VARCHAR(64) NOT NULL,
                        rule_name VARCHAR(128) NOT NULL,
                        tenant_id VARCHAR(64) NOT NULL DEFAULT '{DEFAULT_TENANT_ID}',
                        stage ENUM('pre_trip','in_trip','post_trip') NOT NULL,
                        time_slot ENUM('morning','afternoon','evening','night','all_day')
                            NOT NULL DEFAULT 'all_day',
                        scene ENUM('normal','weather_alert','delay','complaint','manual')
                            NOT NULL DEFAULT 'normal',
                        template_id BIGINT UNSIGNED NULL,
                        priority INT UNSIGNED NOT NULL DEFAULT 100,
                        enabled TINYINT(1) NOT NULL DEFAULT 1,
                        conditions_json JSON NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        PRIMARY KEY (id),
                        UNIQUE KEY uk_rule_code (rule_code),
                        KEY idx_rule_match (stage, time_slot, scene, enabled, priority),
                        CONSTRAINT fk_rule_template FOREIGN KEY (template_id)
                            REFERENCES t_notification_template(id) ON DELETE SET NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
                    """
                )

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS t_notification_rule_channel (
                        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                        rule_id BIGINT UNSIGNED NOT NULL,
                        channel ENUM('sms','wechat_work_group','email') NOT NULL,
                        sort_order TINYINT UNSIGNED NOT NULL DEFAULT 1,
                        PRIMARY KEY (id),
                        UNIQUE KEY uk_rule_channel (rule_id, channel),
                        KEY idx_rule_sort (rule_id, sort_order),
                        CONSTRAINT fk_rule_channel_rule FOREIGN KEY (rule_id)
                            REFERENCES t_notification_rule(id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
                    """
                )

                cursor.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS t_notification_task (
                        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                        task_code VARCHAR(64) NOT NULL,
                        trip_id BIGINT UNSIGNED NULL,
                        team_id VARCHAR(64) NOT NULL DEFAULT '',
                        customer_id VARCHAR(64) NOT NULL,
                        tenant_id VARCHAR(64) NOT NULL DEFAULT '{DEFAULT_TENANT_ID}',
                        notification_type ENUM('pre_trip_reminder','daily_reminder','risk_alert','satisfaction','farewell')
                            NOT NULL,
                        primary_channel ENUM('sms','wechat_work_group','email') NOT NULL DEFAULT 'sms',
                        fallback_channel ENUM('sms','wechat_work_group','email') NULL,
                        rendered_content TEXT NOT NULL,
                        idempotency_key VARCHAR(128) NOT NULL,
                        status ENUM('pending','sent','failed','manual_intervention','skipped')
                            NOT NULL DEFAULT 'pending',
                        retry_count TINYINT UNSIGNED NOT NULL DEFAULT 0,
                        max_retry TINYINT UNSIGNED NOT NULL DEFAULT 2,
                        manual_intervention_required TINYINT(1) NOT NULL DEFAULT 0,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        PRIMARY KEY (id),
                        UNIQUE KEY uk_task_code (task_code),
                        UNIQUE KEY uk_idempotency_key (idempotency_key),
                        KEY idx_task_trip_status (trip_id, status, created_at),
                        CONSTRAINT fk_task_trip FOREIGN KEY (trip_id) REFERENCES t_trip(id) ON DELETE SET NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
                    """
                )

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS t_notification_attempt (
                        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                        task_id BIGINT UNSIGNED NOT NULL,
                        attempt_no TINYINT UNSIGNED NOT NULL DEFAULT 1,
                        channel ENUM('sms','wechat_work_group','email') NOT NULL,
                        ok TINYINT(1) NOT NULL DEFAULT 0,
                        reason VARCHAR(255) NOT NULL DEFAULT '',
                        provider_message VARCHAR(255) NOT NULL DEFAULT '',
                        latency_ms INT UNSIGNED NOT NULL DEFAULT 0,
                        attempted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (id),
                        UNIQUE KEY uk_task_attempt_no (task_id, attempt_no),
                        KEY idx_attempted_at (attempted_at),
                        CONSTRAINT fk_attempt_task FOREIGN KEY (task_id)
                            REFERENCES t_notification_task(id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
                    """
                )

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS t_notification_job (
                        job_id VARCHAR(64) NOT NULL,
                        tenant_id VARCHAR(64) NOT NULL,
                        team_id VARCHAR(64) NOT NULL DEFAULT '',
                        trip_id VARCHAR(64) NOT NULL DEFAULT '',
                        task_id VARCHAR(64) NOT NULL,
                        channel VARCHAR(32) NOT NULL DEFAULT 'sms',
                        status ENUM('pending','processing','retrying','sent','failed','manual_intervention')
                            NOT NULL DEFAULT 'pending',
                        attempt INT UNSIGNED NOT NULL DEFAULT 0,
                        max_attempt INT UNSIGNED NOT NULL DEFAULT 3,
                        next_run_at DATETIME(6) NOT NULL,
                        lease_until DATETIME(6) NULL,
                        worker_id VARCHAR(128) NOT NULL DEFAULT '',
                        last_error VARCHAR(512) NOT NULL DEFAULT '',
                        payload JSON NOT NULL,
                        created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                        updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                            ON UPDATE CURRENT_TIMESTAMP(6),
                        PRIMARY KEY (job_id),
                        KEY idx_job_due (status, next_run_at),
                        KEY idx_job_tenant_status (tenant_id, status),
                        KEY idx_job_task (task_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
                    """
                )

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS t_tenant_notification_config (
                        tenant_id VARCHAR(64) NOT NULL,
                        wechat_webhook_url VARCHAR(512) NOT NULL DEFAULT '',
                        sms_provider VARCHAR(32) NOT NULL DEFAULT '',
                        sms_sign_name VARCHAR(64) NOT NULL DEFAULT '',
                        sms_template_code VARCHAR(64) NOT NULL DEFAULT '',
                        sms_credential_id VARCHAR(64) NOT NULL DEFAULT '',
                        created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                        updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                            ON UPDATE CURRENT_TIMESTAMP(6),
                        PRIMARY KEY (tenant_id)
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
                    if not has_column("t_trip", "ext_data"):
                        cursor.execute(
                            """
                            ALTER TABLE t_trip
                            ADD COLUMN ext_data JSON NULL AFTER tenant_id
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

                # ── 新增: 拆分 trip ext_data，建立独立结构化表 ─────────────────

                # t_trip 扩展列
                if has_table("t_trip"):
                    for col_name, col_def in [
                        ("scene_tags", "JSON NULL COMMENT '特殊场景标签'"),
                    ]:
                        if not has_column("t_trip", col_name):
                            cursor.execute(
                                f"ALTER TABLE t_trip ADD COLUMN {col_name} {col_def}"
                            )

                # t_trip_staff: 行程人员（团期负责人/管家/司机）
                cursor.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS t_trip_staff (
                        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                        trip_id BIGINT UNSIGNED NOT NULL,
                        tenant_id VARCHAR(64) NOT NULL DEFAULT '',
                        role ENUM('manager','concierge','driver') NOT NULL,
                        name VARCHAR(64) NOT NULL DEFAULT '',
                        phone VARCHAR(20) NOT NULL DEFAULT '',
                        PRIMARY KEY (id),
                        UNIQUE KEY uk_trip_role (trip_id, role),
                        KEY idx_staff_tenant (tenant_id),
                        CONSTRAINT fk_staff_trip FOREIGN KEY (trip_id) REFERENCES t_trip(id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
                    """
                )

                # t_guest: 游客独立实体
                cursor.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS t_guest (
                        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                        tenant_id VARCHAR(64) NOT NULL DEFAULT '{DEFAULT_TENANT_ID}',
                        name VARCHAR(64) NOT NULL DEFAULT '',
                        phone VARCHAR(20) NOT NULL DEFAULT '',
                        is_vip TINYINT(1) NOT NULL DEFAULT 0,
                        vip_tagged_at DATETIME NULL,
                        vip_tagged_by VARCHAR(64) NOT NULL DEFAULT '',
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        PRIMARY KEY (id),
                        UNIQUE KEY uk_guest_phone (tenant_id, phone)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
                    """
                )

                # t_trip_guest: 行程-游客多对多
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS t_trip_guest (
                        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                        trip_id BIGINT UNSIGNED NOT NULL,
                        guest_id BIGINT UNSIGNED NOT NULL,
                        PRIMARY KEY (id),
                        UNIQUE KEY uk_trip_guest (trip_id, guest_id),
                        CONSTRAINT fk_tg_trip FOREIGN KEY (trip_id) REFERENCES t_trip(id) ON DELETE CASCADE,
                        CONSTRAINT fk_tg_guest FOREIGN KEY (guest_id) REFERENCES t_guest(id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
                    """
                )

                # t_trip_itinerary: 每日行程表
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS t_trip_itinerary (
                        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                        trip_id BIGINT UNSIGNED NOT NULL,
                        day_number TINYINT UNSIGNED NOT NULL DEFAULT 1,
                        title VARCHAR(128) NOT NULL DEFAULT '',
                        location VARCHAR(128) NOT NULL DEFAULT '',
                        description TEXT,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        PRIMARY KEY (id),
                        UNIQUE KEY uk_trip_day (trip_id, day_number),
                        CONSTRAINT fk_itinerary_trip FOREIGN KEY (trip_id) REFERENCES t_trip(id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
                    """
                )

                # t_workflow_execution: 工作流执行记录
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS t_workflow_execution (
                        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                        trip_id BIGINT UNSIGNED NOT NULL,
                        step_key VARCHAR(64) NOT NULL,
                        completed TINYINT(1) NOT NULL DEFAULT 0,
                        completed_at DATETIME NULL,
                        operator_id VARCHAR(64) NOT NULL DEFAULT '',
                        detail JSON NULL,
                        PRIMARY KEY (id),
                        UNIQUE KEY uk_trip_step (trip_id, step_key),
                        CONSTRAINT fk_wf_trip FOREIGN KEY (trip_id) REFERENCES t_trip(id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
                    """
                )

                # t_audit_log: 独立审计日志表
                cursor.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS t_audit_log (
                        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                        tenant_id VARCHAR(64) NOT NULL DEFAULT '{DEFAULT_TENANT_ID}',
                        operator_id VARCHAR(64) NOT NULL DEFAULT '',
                        action VARCHAR(64) NOT NULL DEFAULT '',
                        target VARCHAR(128) NOT NULL DEFAULT '',
                        detail JSON NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (id),
                        KEY idx_audit_tenant (tenant_id, created_at),
                        KEY idx_audit_operator (operator_id, created_at),
                        KEY idx_audit_target (target, created_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
                    """
                )

                # t_lifecycle_playbook: 流程剧本（已有 seed SQL，这里确保表存在）
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS t_lifecycle_playbook (
                        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                        stage ENUM('pre_trip','in_trip','post_trip') NOT NULL,
                        time_node VARCHAR(64) NOT NULL DEFAULT '',
                        core_work VARCHAR(128) NOT NULL DEFAULT '',
                        action_detail TEXT NOT NULL,
                        sort_order INT UNSIGNED NOT NULL DEFAULT 100,
                        is_active TINYINT(1) NOT NULL DEFAULT 1,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        PRIMARY KEY (id),
                        KEY idx_stage_sort (stage, sort_order)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
                    """
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
        # 使用缓存避免重复读文件
        if collection in self._collection_cache:
            return self._collection_cache[collection]
        items = self._read_collection_json(collection)
        self._collection_cache[collection] = items
        # 自动为常用字段建索引
        if items and collection not in self._indexes:
            if collection == "trips":
                self._build_index(collection, "id", items)
                self._build_index(collection, "status", items)
                self._build_index(collection, "team_id", items)
            elif collection == "guests":
                self._build_index(collection, "id", items)
                self._build_index(collection, "phone", items)
            elif collection in ("trip_staff", "workflow_executions"):
                self._build_index(collection, "trip_id", items)
        return items

    def write_collection(self, collection: str, items: list[dict[str, Any]]) -> None:
        if self._mysql_enabled:
            self._write_collection_mysql(collection, items)
            return
        self._write_collection_json(collection, items)
        # 更新缓存和索引
        self._collection_cache[collection] = items
        if collection in self._indexes:
            del self._indexes[collection]  # 下次读取时重建索引

    def upsert(
        self,
        collection: str,
        item: dict[str, Any],
        key: str = "id",
        key_fields: tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        if self._mysql_enabled:
            return self._upsert_mysql(collection, item, key)

        items = self.read_collection(collection)
        if key_fields:
            existing_index = next(
                (
                    idx
                    for idx, row in enumerate(items)
                    if all(row.get(field) == item.get(field) for field in key_fields)
                ),
                None,
            )
        else:
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

    def acquire_advisory_lock(self, name: str, timeout_seconds: int = 0) -> bool:
        """Acquire a cross-process lock for background workers.

        MySQL uses ``GET_LOCK`` (connection-scoped). The JSON backend uses
        ``flock`` so local multi-process deployments are also protected.
        """
        if name in self._advisory_held:
            return False
        if self._mysql_enabled:
            connection = self._mysql_connect()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT GET_LOCK(%s, %s) AS acquired", (name, timeout_seconds))
                    row = cursor.fetchone() or {}
                acquired = int(row.get("acquired") or 0) == 1
            except Exception:
                connection.close()
                raise
            if not acquired:
                connection.close()
                return False
            self._advisory_held.add(name)
            self._advisory_handles[name] = connection
            return True

        lock_path = Path(self.base_dir or ".") / f".{name}.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = lock_path.open("a+")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            handle.close()
            return False
        self._advisory_held.add(name)
        self._advisory_handles[name] = handle
        return True

    def release_advisory_lock(self, name: str) -> None:
        handle = self._advisory_handles.pop(name, None)
        self._advisory_held.discard(name)
        if handle is None:
            return
        if self._mysql_enabled:
            try:
                with handle.cursor() as cursor:
                    cursor.execute("SELECT RELEASE_LOCK(%s)", (name,))
            finally:
                handle.close()
            return
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()

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
        if collection == "project_notification_configs":
            return self._read_mysql_project_notification_configs()
        if collection == "tenant_notification_configs":
            return self._read_mysql_tenant_notification_configs()
        if collection == "notification_jobs":
            return self._read_mysql_notification_jobs()
        if collection == "notification_rules":
            return self._read_mysql_notification_rules()
        if collection == "notification_attempts":
            return self._read_mysql_notification_attempts()
        if collection == "guests":
            return self._read_mysql_guests()
        if collection == "trip_guests":
            return self._read_mysql_trip_guests()
        if collection == "trip_staff":
            return self._read_mysql_trip_staff()
        if collection == "trip_itineraries":
            return self._read_mysql_trip_itineraries()
        if collection == "workflow_executions":
            return self._read_mysql_workflow_executions()
        if collection == "audit_logs":
            return self._read_mysql_audit_logs()
        if collection == "lifecycle_playbook":
            return self._read_mysql_lifecycle_playbook()
        return self._read_mysql_generic_collection(collection)

    def _write_collection_mysql(self, collection: str, items: list[dict[str, Any]]) -> None:
        if collection == "templates":
            self._write_mysql_templates(items)
            return
        if collection == "project_notification_configs":
            self._write_mysql_project_notification_configs(items)
            return
        if collection == "tenant_notification_configs":
            self._write_mysql_tenant_notification_configs(items)
            return
        if collection == "notification_jobs":
            self._write_mysql_notification_jobs(items)
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
        if collection == "guests":
            self._write_mysql_guests(items)
            return
        if collection == "trip_guests":
            self._write_mysql_trip_guests(items)
            return
        if collection == "trip_staff":
            self._write_mysql_trip_staff(items)
            return
        if collection == "trip_itineraries":
            self._write_mysql_trip_itineraries(items)
            return
        if collection == "workflow_executions":
            self._write_mysql_workflow_executions(items)
            return
        if collection == "lifecycle_playbook":
            self._write_mysql_lifecycle_playbook(items)
            return
        self._write_mysql_generic_collection(collection, items)

    def _upsert_mysql(self, collection: str, item: dict[str, Any], key: str) -> dict[str, Any]:
        if collection == "trips":
            self._upsert_mysql_trip(item, key)
            return item
        if collection == "project_notification_configs":
            self._upsert_mysql_project_notification_config(item, key)
            return item
        if collection == "tenant_notification_configs":
            self._upsert_mysql_tenant_notification_config(item, key)
            return item
        if collection == "notification_jobs":
            self._upsert_mysql_notification_job(item)
            return item
        self._upsert_mysql_generic(collection, item, key)
        return item

    def _delete_mysql(self, collection: str, item_id: str, key: str) -> bool:
        if collection == "trips":
            return self._delete_mysql_trip(item_id)
        if collection == "templates" and key == "id":
            return self._delete_mysql_template(item_id)
        if collection == "project_notification_configs" and key == "project_id":
            return self._delete_mysql_project_notification_config(item_id)
        if collection == "tenant_notification_configs" and key == "tenant_id":
            return self._delete_mysql_tenant_notification_config(item_id)
        if collection == "notification_jobs" and key == "job_id":
            return self._delete_mysql_notification_job(item_id)
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
                cursor.execute("TRUNCATE TABLE t_project_notification_config")
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
                           participants, status, ext_data, owner_user_id, tenant_id, created_at, updated_at
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
            ext_data_raw = row.get("ext_data")
            ext_data = {}
            if isinstance(ext_data_raw, str):
                try:
                    ext_data = json.loads(ext_data_raw)
                except json.JSONDecodeError:
                    pass
            elif isinstance(ext_data_raw, dict):
                ext_data = ext_data_raw

            trip_item = {
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
            # 合并扩展数据 (itinerary, guests)
            if isinstance(ext_data, dict):
                trip_item.update(ext_data)

            items.append(trip_item)
        return items

    def _upsert_mysql_trip(self, item: dict[str, Any], key: str = "id") -> None:
        trip_code = str(item.get(key) or item.get("id") or "").strip()
        if not trip_code:
            raise ValueError("trip id is required")

        team_id = str(item.get("team_id") or item.get("team") or "").strip()
        created_at = _to_mysql_datetime(item.get("created_at"))
        updated_at = _to_mysql_datetime(item.get("updated_at"))

        # 提取扩展数据
        ext_data = {
            "itinerary": item.get("itinerary", []),
            "guests": item.get("guests", []),
        }

        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO t_trip
                    (trip_code, destination, team_id, start_date, end_date, participants, status,
                     ext_data, owner_user_id, tenant_id, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                      destination = VALUES(destination),
                      team_id = VALUES(team_id),
                      start_date = VALUES(start_date),
                      end_date = VALUES(end_date),
                      participants = VALUES(participants),
                      status = VALUES(status),
                      ext_data = VALUES(ext_data),
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
                        json.dumps(ext_data, ensure_ascii=False),
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
                           tenant_id, project_id, stage, time_slot, scene,
                           sms_sign_name, provider_template_code,
                           content, version, is_active, created_at, updated_at
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
                    "project_id": str(row.get("project_id") or ""),
                    "notification_type": _normalize_notification_type(row.get("notification_type")),
                    "channel": _normalize_channel(row.get("channel")),
                    "stage": str(row.get("stage") or ""),
                    "time_slot": str(row.get("time_slot") or ""),
                    "scene": str(row.get("scene") or ""),
                    "sms_sign_name": str(row.get("sms_sign_name") or ""),
                    "provider_template_code": str(row.get("provider_template_code") or ""),
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
                        (template_code, template_name, tenant_id, project_id, notification_type, channel,
                         stage, time_slot, scene, sms_sign_name, provider_template_code, content,
                         version, is_active, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                          version = VALUES(version),
                          is_active = VALUES(is_active),
                          updated_at = VALUES(updated_at)
                        """,
                        (
                            template_code,
                            str(raw.get("name") or ""),
                            _normalize_tenant_id(raw.get("tenant_id")),
                            str(raw.get("project_id") or ""),
                            _normalize_notification_type(raw.get("notification_type")),
                            _normalize_channel(raw.get("channel")),
                            str(raw.get("stage") or ""),
                            str(raw.get("time_slot") or ""),
                            str(raw.get("scene") or ""),
                            str(raw.get("sms_sign_name") or ""),
                            str(raw.get("provider_template_code") or ""),
                            str(raw.get("content") or ""),
                            max(int(raw.get("version") or 1), 1),
                            1 if bool(raw.get("is_active", True)) else 0,
                            _to_mysql_datetime(raw.get("created_at")),
                            _to_mysql_datetime(raw.get("updated_at")),
                        ),
                    )
        finally:
            connection.close()

    def _read_mysql_project_notification_configs(self) -> list[dict[str, Any]]:
        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT tenant_id, project_id, project_name, weather_enabled,
                           qweather_credential_id, qweather_location_id, qweather_lat, qweather_lon,
                           weather_alert_threshold_json, sms_provider, sms_sign_name,
                           sms_template_code_normal, sms_template_code_weather_alert,
                           manual_takeover_target, created_at, updated_at
                    FROM t_project_notification_config
                    ORDER BY updated_at DESC, id DESC
                    """
                )
                rows = cursor.fetchall()
        finally:
            connection.close()

        items: list[dict[str, Any]] = []
        for row in rows:
            items.append(
                {
                    "tenant_id": _normalize_tenant_id(row.get("tenant_id")),
                    "project_id": str(row.get("project_id") or ""),
                    "project_name": str(row.get("project_name") or ""),
                    "weather_enabled": bool(row.get("weather_enabled", True)),
                    "qweather_credential_id": str(row.get("qweather_credential_id") or ""),
                    "qweather_location_id": str(row.get("qweather_location_id") or ""),
                    "qweather_lat": str(row.get("qweather_lat") or ""),
                    "qweather_lon": str(row.get("qweather_lon") or ""),
                    "weather_alert_thresholds": _parse_json_object(
                        row.get("weather_alert_threshold_json")
                    ),
                    "sms_provider": str(row.get("sms_provider") or "aliyun"),
                    "sms_sign_name": str(row.get("sms_sign_name") or ""),
                    "sms_template_code_normal": str(row.get("sms_template_code_normal") or ""),
                    "sms_template_code_weather_alert": str(
                        row.get("sms_template_code_weather_alert") or ""
                    ),
                    "manual_takeover_target": str(row.get("manual_takeover_target") or ""),
                    "created_at": _to_iso_datetime(row.get("created_at")),
                    "updated_at": _to_iso_datetime(row.get("updated_at")),
                }
            )
        return items

    def _write_mysql_project_notification_configs(self, items: list[dict[str, Any]]) -> None:
        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:
                for item in items:
                    self._upsert_mysql_project_notification_config(
                        item, "project_id", cursor=cursor
                    )
        finally:
            connection.close()

    def _upsert_mysql_project_notification_config(
        self,
        item: dict[str, Any],
        key: str = "project_id",
        *,
        cursor: Any | None = None,
    ) -> None:
        project_id = str(item.get(key) or item.get("project_id") or "").strip()
        if not project_id:
            raise ValueError("project_id is required")

        owned_connection = None
        if cursor is None:
            owned_connection = self._mysql_connect()
            cursor = owned_connection.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO t_project_notification_config
                (tenant_id, project_id, project_name, weather_enabled,
                 qweather_credential_id, qweather_location_id, qweather_lat, qweather_lon,
                 weather_alert_threshold_json, sms_provider, sms_sign_name,
                 sms_template_code_normal, sms_template_code_weather_alert,
                 manual_takeover_target, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                  project_name = VALUES(project_name),
                  weather_enabled = VALUES(weather_enabled),
                  qweather_credential_id = VALUES(qweather_credential_id),
                  qweather_location_id = VALUES(qweather_location_id),
                  qweather_lat = VALUES(qweather_lat),
                  qweather_lon = VALUES(qweather_lon),
                  weather_alert_threshold_json = VALUES(weather_alert_threshold_json),
                  sms_provider = VALUES(sms_provider),
                  sms_sign_name = VALUES(sms_sign_name),
                  sms_template_code_normal = VALUES(sms_template_code_normal),
                  sms_template_code_weather_alert = VALUES(sms_template_code_weather_alert),
                  manual_takeover_target = VALUES(manual_takeover_target),
                  updated_at = VALUES(updated_at)
                """,
                (
                    _normalize_tenant_id(item.get("tenant_id")),
                    project_id,
                    str(item.get("project_name") or ""),
                    1 if bool(item.get("weather_enabled", True)) else 0,
                    str(item.get("qweather_credential_id") or ""),
                    str(item.get("qweather_location_id") or ""),
                    str(item.get("qweather_lat") or ""),
                    str(item.get("qweather_lon") or ""),
                    json.dumps(item.get("weather_alert_thresholds") or {}, ensure_ascii=False),
                    str(item.get("sms_provider") or "aliyun"),
                    str(item.get("sms_sign_name") or ""),
                    str(item.get("sms_template_code_normal") or ""),
                    str(item.get("sms_template_code_weather_alert") or ""),
                    str(item.get("manual_takeover_target") or ""),
                    _to_mysql_datetime(item.get("created_at")),
                    _to_mysql_datetime(item.get("updated_at")),
                ),
            )
            if owned_connection is not None:
                owned_connection.commit()
        finally:
            if owned_connection is not None:
                owned_connection.close()

    def _delete_mysql_project_notification_config(self, project_id: str) -> bool:
        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:
                affected = cursor.execute(
                    """
                    DELETE FROM t_project_notification_config
                    WHERE project_id = %s
                    """,
                    (project_id,),
                )
            return affected > 0
        finally:
            connection.close()

    def _read_mysql_tenant_notification_configs(self) -> list[dict[str, Any]]:
        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT tenant_id, wechat_webhook_url, sms_provider, sms_sign_name,
                           sms_template_code, sms_credential_id, created_at, updated_at
                    FROM t_tenant_notification_config
                    ORDER BY updated_at DESC
                    """
                )
                rows = cursor.fetchall()
        finally:
            connection.close()
        return [
            {
                "tenant_id": str(row.get("tenant_id") or ""),
                "wechat_webhook_url": str(row.get("wechat_webhook_url") or ""),
                "sms_provider": str(row.get("sms_provider") or ""),
                "sms_sign_name": str(row.get("sms_sign_name") or ""),
                "sms_template_code": str(row.get("sms_template_code") or ""),
                "sms_credential_id": str(row.get("sms_credential_id") or ""),
                "created_at": _to_iso_datetime(row.get("created_at")),
                "updated_at": _to_iso_datetime(row.get("updated_at")),
            }
            for row in rows
        ]

    def _write_mysql_tenant_notification_configs(self, items: list[dict[str, Any]]) -> None:
        for item in items:
            self._upsert_mysql_tenant_notification_config(item)

    def _upsert_mysql_tenant_notification_config(
        self,
        item: dict[str, Any],
        key: str = "tenant_id",
        *,
        cursor: Any | None = None,
    ) -> None:
        tenant_id = str(item.get(key) or item.get("tenant_id") or "").strip()
        if not tenant_id:
            raise ValueError("tenant_id is required")
        owned_connection = None
        if cursor is None:
            owned_connection = self._mysql_connect()
            cursor = owned_connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO t_tenant_notification_config
                (tenant_id, wechat_webhook_url, sms_provider, sms_sign_name,
                 sms_template_code, sms_credential_id, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                  wechat_webhook_url = VALUES(wechat_webhook_url),
                  sms_provider = VALUES(sms_provider),
                  sms_sign_name = VALUES(sms_sign_name),
                  sms_template_code = VALUES(sms_template_code),
                  sms_credential_id = VALUES(sms_credential_id),
                  updated_at = VALUES(updated_at)
                """,
                (
                    tenant_id,
                    str(item.get("wechat_webhook_url") or ""),
                    str(item.get("sms_provider") or ""),
                    str(item.get("sms_sign_name") or ""),
                    str(item.get("sms_template_code") or ""),
                    str(item.get("sms_credential_id") or ""),
                    _to_mysql_datetime(item.get("created_at")),
                    _to_mysql_datetime(item.get("updated_at")),
                ),
            )
            if owned_connection is not None:
                owned_connection.commit()
        finally:
            if owned_connection is not None:
                owned_connection.close()

    def _delete_mysql_tenant_notification_config(self, tenant_id: str) -> bool:
        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:
                affected = cursor.execute(
                    "DELETE FROM t_tenant_notification_config WHERE tenant_id = %s",
                    (tenant_id,),
                )
            return affected > 0
        finally:
            connection.close()

    def _read_mysql_notification_jobs(self) -> list[dict[str, Any]]:
        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT payload
                    FROM t_notification_job
                    ORDER BY created_at ASC
                    """
                )
                rows = cursor.fetchall()
        finally:
            connection.close()
        items: list[dict[str, Any]] = []
        for row in rows:
            payload = row.get("payload")
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError:
                    continue
            if isinstance(payload, dict):
                items.append(payload)
        return items

    def _write_mysql_notification_jobs(self, items: list[dict[str, Any]]) -> None:
        for item in items:
            self._upsert_mysql_notification_job(item)

    def _upsert_mysql_notification_job(self, item: dict[str, Any]) -> None:
        job_id = str(item.get("job_id") or "").strip()
        if not job_id:
            return
        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO t_notification_job
                    (job_id, tenant_id, team_id, trip_id, task_id, channel, status,
                     attempt, max_attempt, next_run_at, lease_until, worker_id,
                     last_error, payload, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                      status = VALUES(status),
                      attempt = VALUES(attempt),
                      next_run_at = VALUES(next_run_at),
                      lease_until = VALUES(lease_until),
                      worker_id = VALUES(worker_id),
                      last_error = VALUES(last_error),
                      payload = VALUES(payload),
                      updated_at = VALUES(updated_at)
                    """,
                    (
                        job_id,
                        str(item.get("tenant_id") or ""),
                        str(item.get("team_id") or ""),
                        str(item.get("trip_id") or ""),
                        str(item.get("task_id") or ""),
                        str(item.get("channel") or "sms"),
                        str(item.get("status") or "pending"),
                        int(item.get("attempt") or 0),
                        int(item.get("max_attempt") or 3),
                        _to_mysql_datetime(item.get("next_run_at")),
                        _to_mysql_datetime(item.get("lease_until")) if item.get("lease_until") else None,
                        str(item.get("worker_id") or ""),
                        str(item.get("last_error") or "")[:512],
                        json.dumps(item, ensure_ascii=False, default=_json_default),
                        _to_mysql_datetime(item.get("created_at")),
                        _to_mysql_datetime(item.get("updated_at")),
                    ),
                )
        finally:
            connection.close()

    def _delete_mysql_notification_job(self, job_id: str) -> bool:
        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:
                affected = cursor.execute(
                    "DELETE FROM t_notification_job WHERE job_id = %s",
                    (job_id,),
                )
            return affected > 0
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
                if not template_rows:
                    now = datetime.now(tz=UTC).replace(tzinfo=None)
                    cursor.execute(
                        """
                        INSERT INTO t_notification_template
                        (template_code, template_name, tenant_id, project_id, notification_type, channel,
                         stage, time_slot, scene, sms_sign_name, provider_template_code, content,
                         version, is_active, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            "tpl-bootstrap-default",
                            "Bootstrap 默认模板",
                            DEFAULT_TENANT_ID,
                            "",
                            "daily_reminder",
                            "sms",
                            "",
                            "",
                            "",
                            "",
                            "",
                            "{{customer_name}}，您好，请留意行程通知。",
                            1,
                            1,
                            now,
                            now,
                        ),
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

    # ── 新增表 MySQL 读写方法 ────────────────────────────────────────────────

    def _read_mysql_guests(self) -> list[dict[str, Any]]:
        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM t_guest ORDER BY id")
                rows = cursor.fetchall() or []
        finally:
            connection.close()
        items: list[dict[str, Any]] = []
        for row in rows:
            items.append({
                "id": str(row.get("id")),
                "tenant_id": row.get("tenant_id", ""),
                "name": row.get("name", ""),
                "phone": row.get("phone", ""),
                "is_vip": bool(row.get("is_vip")),
                "vip_tagged_at": _to_iso_datetime(row.get("vip_tagged_at")),
                "vip_tagged_by": row.get("vip_tagged_by", ""),
                "created_at": _to_iso_datetime(row.get("created_at")),
                "updated_at": _to_iso_datetime(row.get("updated_at")),
            })
        return items

    def _write_mysql_guests(self, items: list[dict[str, Any]]) -> None:
        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:
                for item in items:
                    guest_id = str(item.get("id") or "")
                    cursor.execute(
                        """
                        INSERT INTO t_guest (id, tenant_id, name, phone, is_vip, vip_tagged_at, vip_tagged_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            name = VALUES(name), phone = VALUES(phone),
                            is_vip = VALUES(is_vip), vip_tagged_at = VALUES(vip_tagged_at),
                            vip_tagged_by = VALUES(vip_tagged_by)
                        """,
                        (
                            int(guest_id) if guest_id.isdigit() else 0,
                            item.get("tenant_id", "tenant-a"),
                            item.get("name", ""),
                            item.get("phone", ""),
                            1 if item.get("is_vip") else 0,
                            _to_mysql_datetime(item.get("vip_tagged_at")),
                            item.get("vip_tagged_by", ""),
                        ),
                    )
            connection.commit()
        finally:
            connection.close()

    def _read_mysql_trip_guests(self) -> list[dict[str, Any]]:
        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM t_trip_guest ORDER BY id")
                rows = cursor.fetchall() or []
        finally:
            connection.close()
        return [{"id": str(r["id"]), "trip_id": str(r["trip_id"]), "guest_id": str(r["guest_id"])} for r in rows]

    def _write_mysql_trip_guests(self, items: list[dict[str, Any]]) -> None:
        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:
                for item in items:
                    tid = int(str(item.get("trip_id") or "0"))
                    gid = int(str(item.get("guest_id") or "0"))
                    if not tid or not gid:
                        continue
                    cursor.execute(
                        """
                        INSERT IGNORE INTO t_trip_guest (trip_id, guest_id) VALUES (%s, %s)
                        """,
                        (tid, gid),
                    )
            connection.commit()
        finally:
            connection.close()

    def _read_mysql_trip_staff(self) -> list[dict[str, Any]]:
        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM t_trip_staff ORDER BY id")
                rows = cursor.fetchall() or []
        finally:
            connection.close()
        return [
            {
                "id": str(r["id"]),
                "trip_id": str(r["trip_id"]),
                "role": r["role"],
                "name": r.get("name", ""),
                "phone": r.get("phone", ""),
            }
            for r in rows
        ]

    def _write_mysql_trip_staff(self, items: list[dict[str, Any]]) -> None:
        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:
                for item in items:
                    tid = int(str(item.get("trip_id") or "0"))
                    role = item.get("role", "")
                    if not tid or not role:
                        continue
                    cursor.execute(
                        """
                        INSERT INTO t_trip_staff (trip_id, role, name, phone)
                        VALUES (%s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE name = VALUES(name), phone = VALUES(phone)
                        """,
                        (tid, role, item.get("name", ""), item.get("phone", "")),
                    )
            connection.commit()
        finally:
            connection.close()

    def _read_mysql_trip_itineraries(self) -> list[dict[str, Any]]:
        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM t_trip_itinerary ORDER BY trip_id, day_number")
                rows = cursor.fetchall() or []
        finally:
            connection.close()
        return [
            {
                "id": str(r["id"]),
                "trip_id": str(r["trip_id"]),
                "day_number": int(r.get("day_number", 1)),
                "title": r.get("title", ""),
                "location": r.get("location", ""),
                "description": r.get("description", ""),
            }
            for r in rows
        ]

    def _write_mysql_trip_itineraries(self, items: list[dict[str, Any]]) -> None:
        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:
                for item in items:
                    tid = int(str(item.get("trip_id") or "0"))
                    day = int(item.get("day_number", 1))
                    if not tid:
                        continue
                    cursor.execute(
                        """
                        INSERT INTO t_trip_itinerary (trip_id, day_number, title, location, description)
                        VALUES (%s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            title = VALUES(title), location = VALUES(location), description = VALUES(description)
                        """,
                        (tid, day, item.get("title", ""), item.get("location", ""), item.get("description", "")),
                    )
            connection.commit()
        finally:
            connection.close()

    def _read_mysql_workflow_executions(self) -> list[dict[str, Any]]:
        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM t_workflow_execution ORDER BY id")
                rows = cursor.fetchall() or []
        finally:
            connection.close()
        return [
            {
                "id": str(r["id"]),
                "trip_id": str(r["trip_id"]),
                "step_key": r.get("step_key", ""),
                "completed": bool(r.get("completed")),
                "completed_at": _to_iso_datetime(r.get("completed_at")),
                "operator_id": r.get("operator_id", ""),
                "detail": _parse_json_object(r.get("detail")),
            }
            for r in rows
        ]

    def _write_mysql_workflow_executions(self, items: list[dict[str, Any]]) -> None:
        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:
                for item in items:
                    tid = int(str(item.get("trip_id") or "0"))
                    step_key = item.get("step_key", "")
                    if not tid or not step_key:
                        continue
                    detail = json.dumps(item.get("detail") or {}, ensure_ascii=False)
                    cursor.execute(
                        """
                        INSERT INTO t_workflow_execution (trip_id, step_key, completed, completed_at, operator_id, detail)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            completed = VALUES(completed), completed_at = VALUES(completed_at),
                            operator_id = VALUES(operator_id), detail = VALUES(detail)
                        """,
                        (
                            tid, step_key,
                            1 if item.get("completed") else 0,
                            _to_mysql_datetime(item.get("completed_at")),
                            item.get("operator_id", ""),
                            detail,
                        ),
                    )
            connection.commit()
        finally:
            connection.close()

    def _read_mysql_audit_logs(self) -> list[dict[str, Any]]:
        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM t_audit_log ORDER BY created_at DESC LIMIT 500")
                rows = cursor.fetchall() or []
        finally:
            connection.close()
        return [
            {
                "id": str(r["id"]),
                "tenant_id": r.get("tenant_id", ""),
                "operator_id": r.get("operator_id", ""),
                "action": r.get("action", ""),
                "target": r.get("target", ""),
                "detail": _parse_json_object(r.get("detail")),
                "created_at": _to_iso_datetime(r.get("created_at")),
            }
            for r in rows
        ]

    def _read_mysql_lifecycle_playbook(self) -> list[dict[str, Any]]:
        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM t_lifecycle_playbook WHERE is_active = 1 ORDER BY sort_order")
                rows = cursor.fetchall() or []
        finally:
            connection.close()
        return [
            {
                "id": str(r["id"]),
                "stage": r.get("stage", ""),
                "time_node": r.get("time_node", ""),
                "core_work": r.get("core_work", ""),
                "action_detail": r.get("action_detail", ""),
                "sort_order": int(r.get("sort_order", 100)),
                "is_active": bool(r.get("is_active", True)),
                "created_at": _to_iso_datetime(r.get("created_at")),
                "updated_at": _to_iso_datetime(r.get("updated_at")),
            }
            for r in rows
        ]

    def _write_mysql_lifecycle_playbook(self, items: list[dict[str, Any]]) -> None:
        connection = self._mysql_connect()
        try:
            with connection.cursor() as cursor:
                for item in items:
                    rid = int(str(item.get("id") or "0"))
                    cursor.execute(
                        """
                        INSERT INTO t_lifecycle_playbook (id, stage, time_node, core_work, action_detail, sort_order, is_active)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            stage = VALUES(stage), time_node = VALUES(time_node),
                            core_work = VALUES(core_work), action_detail = VALUES(action_detail),
                            sort_order = VALUES(sort_order), is_active = VALUES(is_active)
                        """,
                        (
                            rid, item.get("stage", ""), item.get("time_node", ""),
                            item.get("core_work", ""), item.get("action_detail", ""),
                            int(item.get("sort_order", 100)),
                            1 if item.get("is_active", True) else 0,
                        ),
                    )
            connection.commit()
        finally:
            connection.close()

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
        # ``item_key`` is written from the preferred key at upsert time, so it
        # can be deleted directly regardless of whether the key is ``id`` or a
        # domain identifier (tenant_id, username, token hash, ...).
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

    def list(self, tenant_id: str | None = None) -> list[dict[str, Any]]:
        items = self.store.read_collection(self.collection)
        if tenant_id is None:
            return items
        return [item for item in items if str(item.get("tenant_id") or "") == tenant_id]

    def get(self, trip_id: str, tenant_id: str | None = None) -> dict[str, Any] | None:
        for item in self.list(tenant_id=tenant_id):
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


@dataclass(slots=True)
class TripStaffRepository:
    """行程人员仓库（团期负责人/管家/司机）。"""
    store: JsonFileStore
    collection: str = "trip_staff"

    def get_by_trip(self, trip_id: str) -> list[dict[str, Any]]:
        rows = self.store.read_collection(self.collection)
        return [r for r in rows if str(r.get("trip_id")) == trip_id]

    def upsert(self, trip_id: str, role: str, name: str, phone: str) -> dict[str, Any]:
        rows = self.store.read_collection(self.collection)
        existing = next((r for r in rows if str(r.get("trip_id")) == trip_id and r.get("role") == role), None)
        item = {"trip_id": trip_id, "role": role, "name": name, "phone": phone}
        if existing:
            existing.update(item)
        else:
            item["id"] = f"staff-{trip_id}-{role}"
            rows.append(item)
        self.store.write_collection(self.collection, rows)
        return existing or item

    def put_staff_batch(self, trip_id: str, staff_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows = self.store.read_collection(self.collection)
        rows = [r for r in rows if str(r.get("trip_id")) != trip_id]
        results = []
        for s in staff_list:
            item = {
                "id": f"staff-{trip_id}-{s.get('role','')}",
                "trip_id": trip_id,
                "role": s.get("role", ""),
                "name": s.get("name", ""),
                "phone": s.get("phone", ""),
            }
            rows.append(item)
            results.append(item)
        self.store.write_collection(self.collection, rows)
        return results


@dataclass(slots=True)
class GuestRepository:
    """游客仓库（独立实体）。"""
    store: JsonFileStore
    collection: str = "guests"

    def list(self, tenant_id: str = "tenant-a") -> list[dict[str, Any]]:
        return [r for r in self.store.read_collection(self.collection) if r.get("tenant_id") == tenant_id]

    def get(self, guest_id: str) -> dict[str, Any] | None:
        for r in self.store.read_collection(self.collection):
            if str(r.get("id")) == guest_id:
                return r
        return None

    def get_by_phone(self, phone: str, tenant_id: str = "tenant-a") -> dict[str, Any] | None:
        for r in self.store.read_collection(self.collection):
            if r.get("phone") == phone and r.get("tenant_id") == tenant_id:
                return r
        return None

    def create(self, item: dict[str, Any]) -> dict[str, Any]:
        import uuid
        item["id"] = str(item.get("id") or f"guest-{uuid.uuid4().hex[:10]}")
        item.setdefault("tenant_id", "tenant-a")
        item.setdefault("is_vip", False)
        rows = self.store.read_collection(self.collection)
        rows.append(item)
        self.store.write_collection(self.collection, rows)
        return item

    def update(self, guest_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        rows = self.store.read_collection(self.collection)
        for r in rows:
            if str(r.get("id")) == guest_id:
                r.update(patch)
                self.store.write_collection(self.collection, rows)
                return r
        return None

    def delete(self, guest_id: str) -> bool:
        rows = self.store.read_collection(self.collection)
        new_rows = [r for r in rows if str(r.get("id")) != guest_id]
        if len(new_rows) == len(rows):
            return False
        self.store.write_collection(self.collection, new_rows)
        return True


@dataclass(slots=True)
class TripGuestRepository:
    """行程-游客关联仓库。"""
    store: JsonFileStore
    collection: str = "trip_guests"

    def get_guest_ids(self, trip_id: str) -> list[str]:
        rows = self.store.read_collection(self.collection)
        return [str(r["guest_id"]) for r in rows if str(r.get("trip_id")) == trip_id]

    def get_trip_ids(self, guest_id: str) -> list[str]:
        rows = self.store.read_collection(self.collection)
        return [str(r["trip_id"]) for r in rows if str(r.get("guest_id")) == guest_id]

    def link(self, trip_id: str, guest_id: str) -> dict[str, Any]:
        rows = self.store.read_collection(self.collection)
        existing = next((r for r in rows if str(r.get("trip_id")) == trip_id and str(r.get("guest_id")) == guest_id), None)
        if existing:
            return existing
        item = {"id": f"tg-{trip_id}-{guest_id}", "trip_id": trip_id, "guest_id": guest_id}
        rows.append(item)
        self.store.write_collection(self.collection, rows)
        return item

    def unlink(self, trip_id: str, guest_id: str) -> bool:
        rows = self.store.read_collection(self.collection)
        new_rows = [r for r in rows if not (str(r.get("trip_id")) == trip_id and str(r.get("guest_id")) == guest_id)]
        if len(new_rows) == len(rows):
            return False
        self.store.write_collection(self.collection, new_rows)
        return True


@dataclass(slots=True)
class TripItineraryRepository:
    """每日行程表仓库。"""
    store: JsonFileStore
    collection: str = "trip_itineraries"

    def get_by_trip(self, trip_id: str) -> list[dict[str, Any]]:
        rows = self.store.read_collection(self.collection)
        return sorted(
            [r for r in rows if str(r.get("trip_id")) == trip_id],
            key=lambda r: int(r.get("day_number", 1)),
        )

    def upsert(self, trip_id: str, day_number: int, item: dict[str, Any]) -> dict[str, Any]:
        rows = self.store.read_collection(self.collection)
        existing = next(
            (r for r in rows if str(r.get("trip_id")) == trip_id and int(r.get("day_number", 1)) == day_number),
            None,
        )
        item["trip_id"] = trip_id
        item["day_number"] = day_number
        if existing:
            existing.update(item)
        else:
            item["id"] = f"itin-{trip_id}-d{day_number}"
            rows.append(item)
        self.store.write_collection(self.collection, rows)
        return existing or item

    def replace_all(self, trip_id: str, days: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows = self.store.read_collection(self.collection)
        rows = [r for r in rows if str(r.get("trip_id")) != trip_id]
        results = []
        for i, d in enumerate(days, 1):
            item = {
                "id": f"itin-{trip_id}-d{i}",
                "trip_id": trip_id,
                "day_number": i,
                "title": d.get("title", ""),
                "location": d.get("location", ""),
                "description": d.get("description", ""),
            }
            rows.append(item)
            results.append(item)
        self.store.write_collection(self.collection, rows)
        return results


@dataclass(slots=True)
class WorkflowExecutionRepository:
    """工作流执行记录仓库（替代 trip.workflow_status JSON）。"""
    store: JsonFileStore
    collection: str = "workflow_executions"

    def get_by_trip(self, trip_id: str) -> list[dict[str, Any]]:
        return [r for r in self.store.read_collection(self.collection) if str(r.get("trip_id")) == trip_id]

    def mark(self, trip_id: str, step_key: str, operator_id: str = "", detail: dict | None = None) -> dict[str, Any]:
        rows = self.store.read_collection(self.collection)
        existing = next(
            (r for r in rows if str(r.get("trip_id")) == trip_id and r.get("step_key") == step_key),
            None,
        )
        now = datetime.now(tz=UTC).isoformat()
        item = {
            "trip_id": trip_id,
            "step_key": step_key,
            "completed": True,
            "completed_at": now,
            "operator_id": operator_id,
            "detail": detail or {},
        }
        if existing:
            existing.update(item)
        else:
            item["id"] = f"wf-{trip_id}-{step_key}"
            rows.append(item)
        self.store.write_collection(self.collection, rows)
        return existing or item

    def get_status_map(self, trip_id: str) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for r in self.get_by_trip(trip_id):
            result[r["step_key"]] = r
        return result


@dataclass(slots=True)
class LifecyclePlaybookRepository:
    """流程剧本仓库。"""
    store: JsonFileStore
    collection: str = "lifecycle_playbook"

    def list_all(self) -> list[dict[str, Any]]:
        rows = self.store.read_collection(self.collection)
        return sorted(rows, key=lambda r: int(r.get("sort_order", 100)))

    def list_by_stage(self, stage: str) -> list[dict[str, Any]]:
        return [r for r in self.list_all() if r.get("stage") == stage]


@dataclass(slots=True)
class ProjectNotificationConfigRepository:
    store: JsonFileStore
    collection: str = "project_notification_configs"

    def list(self, *, tenant_id: str | None = None) -> list[dict[str, Any]]:
        items = self.store.read_collection(self.collection)
        if not tenant_id:
            return items
        return [item for item in items if item.get("tenant_id") == tenant_id]

    def get(self, project_id: str, *, tenant_id: str) -> dict[str, Any] | None:
        for item in self.list(tenant_id=tenant_id):
            if str(item.get("project_id") or "") == project_id:
                return item
        return None

    def upsert(self, payload: dict[str, Any]) -> dict[str, Any]:
        item = dict(payload)
        item["tenant_id"] = _normalize_tenant_id(item.get("tenant_id"))
        item["project_id"] = str(item.get("project_id") or "").strip()
        if not item["project_id"]:
            raise ValueError("project_id is required")
        item["project_name"] = str(item.get("project_name") or "")
        item["weather_enabled"] = bool(item.get("weather_enabled", True))
        item["qweather_credential_id"] = str(item.get("qweather_credential_id") or "")
        item["qweather_location_id"] = str(item.get("qweather_location_id") or "")
        item["qweather_lat"] = str(item.get("qweather_lat") or "")
        item["qweather_lon"] = str(item.get("qweather_lon") or "")
        item["weather_alert_thresholds"] = _parse_json_object(item.get("weather_alert_thresholds"))
        item["sms_provider"] = str(item.get("sms_provider") or "aliyun")
        item["sms_sign_name"] = str(item.get("sms_sign_name") or "")
        item["sms_template_code_normal"] = str(item.get("sms_template_code_normal") or "")
        item["sms_template_code_weather_alert"] = str(
            item.get("sms_template_code_weather_alert") or ""
        )
        item["manual_takeover_target"] = str(item.get("manual_takeover_target") or "")
        if not item.get("created_at"):
            item["created_at"] = datetime.now(tz=UTC).isoformat()
        item["updated_at"] = datetime.now(tz=UTC).isoformat()
        return self.store.upsert(
            self.collection,
            item,
            key="project_id",
            key_fields=("tenant_id", "project_id"),
        )
