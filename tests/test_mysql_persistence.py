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
