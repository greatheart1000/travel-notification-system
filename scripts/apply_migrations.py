#!/usr/bin/env python3
"""Apply SQL migrations once per environment.

The application's MySQL store creates its base schema on startup. This runner
is intentionally small and dependency-free: it tracks applied files in
``t_schema_migrations`` and tolerates "already exists" errors from repeated
deployments.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

IGNORED_MYSQL_ERRORS = {
    1050,  # table already exists
    1060,  # duplicate column name
    1061,  # duplicate key name
    1091,  # can't drop; check that column/key exists
    1146,  # table doesn't exist (handled by base schema creation)
    1826,  # duplicate foreign key constraint name
}


def split_sql(text: str) -> list[str]:
    cleaned_lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("--") or line.startswith("#"):
            continue
        # Strip trailing comments that are not inside a quoted string.
        if "--" in line and "'" not in line and '"' not in line:
            line = line.split("--", 1)[0].rstrip()
        cleaned_lines.append(line)
    joined = "\n".join(cleaned_lines)
    statements = []
    for chunk in joined.split(";"):
        statement = chunk.strip()
        if statement:
            statements.append(statement)
    return statements


def main() -> int:
    backend = os.getenv("TRAVEL_NOTIFICATION_PERSISTENCE_BACKEND", "mysql").strip().lower()
    if backend != "mysql":
        print(f"[migrations] persistence backend is {backend}; skipping SQL migrations")
        return 0

    repo_root = Path(__file__).resolve().parents[1]
    migrations_dir = repo_root / "docs" / "migrations"
    if not migrations_dir.is_dir():
        print("[migrations] no docs/migrations directory; nothing to do")
        return 0

    # Importing the store creates the base schema (t_collection_store, queue,
    # tenant config, etc.) before additive migrations run.
    sys.path.insert(0, str(repo_root / "src"))
    from app.modules.integration.persistence import JsonFileStore

    JsonFileStore()

    import pymysql

    connection = pymysql.connect(
        host=os.getenv("TRAVEL_NOTIFICATION_MYSQL_HOST", "mysql"),
        port=int(os.getenv("TRAVEL_NOTIFICATION_MYSQL_PORT", "3306")),
        user=os.getenv("TRAVEL_NOTIFICATION_MYSQL_USER", "root"),
        password=os.getenv("TRAVEL_NOTIFICATION_MYSQL_PASSWORD", ""),
        database=os.getenv("TRAVEL_NOTIFICATION_MYSQL_DATABASE", "travel_notification_system"),
        charset="utf8mb4",
        autocommit=True,
    )

    applied: set[str] = set()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS t_schema_migrations (
                    version VARCHAR(255) NOT NULL,
                    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (version)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cursor.execute("SELECT version FROM t_schema_migrations")
            applied = {str(row[0]) for row in cursor.fetchall()}

            for path in sorted(migrations_dir.glob("*.sql")):
                version = path.name
                if version in applied:
                    print(f"[migrations] skip {version} (already applied)")
                    continue
                print(f"[migrations] applying {version}")
                for statement in split_sql(path.read_text(encoding="utf-8")):
                    try:
                        cursor.execute(statement)
                    except pymysql.err.MySQLError as exc:
                        code = exc.args[0] if exc.args else None
                        if code in IGNORED_MYSQL_ERRORS:
                            print(f"[migrations]   tolerated MySQL error {code}: {exc}")
                            continue
                        raise
                cursor.execute(
                    "INSERT INTO t_schema_migrations (version) VALUES (%s)",
                    (version,),
                )
    finally:
        connection.close()

    print("[migrations] done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
