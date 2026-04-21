from __future__ import annotations

import os

import pymysql
from fastapi.testclient import TestClient

from app.api.http import app, reset_state
from app.modules.integration.persistence import JsonFileStore
from app.services.template_service import TemplateService


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def _mysql_connect() -> pymysql.connections.Connection:
    host = os.getenv("TRAVEL_NOTIFICATION_MYSQL_HOST", "127.0.0.1")
    user = os.getenv("TRAVEL_NOTIFICATION_MYSQL_USER", "root")
    password = os.getenv("TRAVEL_NOTIFICATION_MYSQL_PASSWORD", "123456")
    database = os.getenv("TRAVEL_NOTIFICATION_MYSQL_DATABASE", "travel_notification_system")
    port = int(os.getenv("TRAVEL_NOTIFICATION_MYSQL_PORT", "3306"))
    return pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        port=port,
        charset="utf8mb4",
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
    )


def test_trip_and_notification_attempt_are_persisted_to_mysql_tables() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)

    token = _login(client, "user", "123456")
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/api/trips",
        headers=headers,
        json={
            "destination": "天山环线",
            "team": "TEAM-MYSQL-001",
            "start_date": "2026-07-01",
            "end_date": "2026-07-05",
            "participants": 10,
        },
    )
    assert created.status_code == 201
    trip_id = created.json()["data"]["trip"]["id"]

    with _mysql_connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT trip_code, destination, team_id FROM t_trip WHERE trip_code = %s",
                (trip_id,),
            )
            trip_row = cursor.fetchone()
            assert trip_row is not None
            assert trip_row["destination"] == "天山环线"
            assert trip_row["team_id"] == "TEAM-MYSQL-001"

            cursor.execute(
                """
                SELECT a.id
                FROM t_notification_attempt AS a
                JOIN t_notification_task AS t ON t.id = a.task_id
                JOIN t_trip AS tr ON tr.id = t.trip_id
                WHERE tr.trip_code = %s
                """,
                (trip_id,),
            )
            attempts = cursor.fetchall()
            assert len(attempts) >= 1


def test_app_context_defaults_to_mysql_backend() -> None:
    reset_state(purge_persistence=False)
    ctx = app.state.ctx
    assert str(ctx.store.base_dir).startswith("mysql://")
    assert getattr(ctx.store, "_mysql_enabled", False) is True


def test_mysql_schema_and_seeded_rows_keep_tenant_id() -> None:
    reset_state(purge_persistence=True)

    with _mysql_connect() as connection:
        with connection.cursor() as cursor:
            for table in (
                "t_trip",
                "t_notification_template",
                "t_notification_rule",
                "t_notification_task",
            ):
                cursor.execute(f"SHOW COLUMNS FROM {table} LIKE 'tenant_id'")
                assert cursor.fetchone() is not None

            cursor.execute(
                "SELECT COUNT(*) AS cnt FROM t_trip WHERE tenant_id IS NULL OR tenant_id = ''"
            )
            trip_missing = int((cursor.fetchone() or {}).get("cnt", 0))
            assert trip_missing == 0

            cursor.execute(
                "SELECT COUNT(*) AS cnt FROM t_notification_template WHERE tenant_id IS NULL OR tenant_id = ''"
            )
            template_missing = int((cursor.fetchone() or {}).get("cnt", 0))
            assert template_missing == 0

            cursor.execute(
                "SELECT COUNT(*) AS cnt FROM t_notification_rule WHERE tenant_id IS NULL OR tenant_id = ''"
            )
            rule_missing = int((cursor.fetchone() or {}).get("cnt", 0))
            assert rule_missing == 0


def test_template_service_loads_latest_version_for_same_template_code(monkeypatch) -> None:
    monkeypatch.setenv("TRAVEL_NOTIFICATION_MYSQL_HOST", "127.0.0.1")
    monkeypatch.setenv("TRAVEL_NOTIFICATION_MYSQL_PORT", "3306")
    monkeypatch.setenv("TRAVEL_NOTIFICATION_MYSQL_USER", "root")
    monkeypatch.setenv("TRAVEL_NOTIFICATION_MYSQL_PASSWORD", "123456")
    monkeypatch.setenv("TRAVEL_NOTIFICATION_MYSQL_DATABASE", "travel_notification_system")

    template_code = "tpl-version-selection-case"
    with _mysql_connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM t_notification_template WHERE template_code = %s", (template_code,)
            )
            cursor.execute(
                """
                INSERT INTO t_notification_template
                (template_code, template_name, notification_type, channel, content, version, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (template_code, "版本一", "daily_reminder", "sms", "v1", 1, 1),
            )
            cursor.execute(
                """
                INSERT INTO t_notification_template
                (template_code, template_name, notification_type, channel, content, version, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (template_code, "版本二", "daily_reminder", "sms", "v2", 2, 1),
            )

    service = TemplateService(store=JsonFileStore())
    template = service.get_notification_template(template_code)
    assert template is not None
    assert template.version == 2
    assert template.name == "版本二"


def test_project_notification_config_persists_to_mysql_table() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)
    token = _login(client, "admin", "123456")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.put(
        "/api/project-configs/proj-xinjiang",
        headers=headers,
        json={
            "project_name": "新疆阿勒泰团",
            "weather_enabled": True,
            "qweather_location_id": "101130101",
            "weather_alert_thresholds": {"warning_levels": ["orange", "red"]},
            "sms_sign_name": "新疆团",
            "sms_template_code_normal": "SMS_XJ_NORMAL",
            "sms_template_code_weather_alert": "SMS_XJ_ALERT",
        },
    )
    assert response.status_code == 200

    with _mysql_connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT project_id, project_name, sms_sign_name,
                       sms_template_code_normal, sms_template_code_weather_alert,
                       weather_alert_threshold_json
                FROM t_project_notification_config
                WHERE tenant_id = %s AND project_id = %s
                """,
                ("tenant-a", "proj-xinjiang"),
            )
            row = cursor.fetchone()
            assert row is not None
            assert row["project_name"] == "新疆阿勒泰团"
            assert row["sms_sign_name"] == "新疆团"
            assert row["sms_template_code_normal"] == "SMS_XJ_NORMAL"
            assert row["sms_template_code_weather_alert"] == "SMS_XJ_ALERT"
            assert "orange" in str(row["weather_alert_threshold_json"])


def test_mysql_schema_contains_project_notification_config_table() -> None:
    reset_state(purge_persistence=True)

    with _mysql_connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SHOW COLUMNS FROM t_project_notification_config")
            columns = {row["Field"] for row in cursor.fetchall()}

    assert {
        "tenant_id",
        "project_id",
        "project_name",
        "weather_alert_threshold_json",
        "sms_sign_name",
        "sms_template_code_normal",
        "sms_template_code_weather_alert",
    }.issubset(columns)


def test_mysql_template_schema_migration_does_not_depend_on_rule_table() -> None:
    with _mysql_connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            cursor.execute("DROP TABLE IF EXISTS t_notification_attempt")
            cursor.execute("DROP TABLE IF EXISTS t_notification_task")
            cursor.execute("DROP TABLE IF EXISTS t_notification_rule_channel")
            cursor.execute("DROP TABLE IF EXISTS t_notification_rule")
            cursor.execute("DROP TABLE IF EXISTS t_notification_template")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            cursor.execute(
                """
                CREATE TABLE t_notification_template (
                    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    template_code VARCHAR(64) NOT NULL,
                    template_name VARCHAR(128) NOT NULL,
                    notification_type ENUM(
                        'pre_trip_reminder',
                        'daily_reminder',
                        'risk_alert',
                        'satisfaction',
                        'farewell'
                    ) NOT NULL DEFAULT 'daily_reminder',
                    channel ENUM('sms','wechat_work_group','email') NOT NULL DEFAULT 'sms',
                    content TEXT NOT NULL,
                    version INT UNSIGNED NOT NULL DEFAULT 1,
                    is_active TINYINT(1) NOT NULL DEFAULT 1,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    UNIQUE KEY uk_template_code_version (template_code, version)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
                """
            )

    JsonFileStore()

    with _mysql_connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES LIKE 't_notification_rule'")
            assert cursor.fetchone() is not None
            cursor.execute("SHOW COLUMNS FROM t_notification_template")
            columns = {row["Field"] for row in cursor.fetchall()}

    assert {
        "tenant_id",
        "project_id",
        "stage",
        "time_slot",
        "scene",
        "sms_sign_name",
        "provider_template_code",
    }.issubset(columns)
