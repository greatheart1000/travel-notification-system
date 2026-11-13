#!/usr/bin/env sh
set -eu

BACKEND="${TRAVEL_NOTIFICATION_PERSISTENCE_BACKEND:-mysql}"

if [ "$BACKEND" = "mysql" ]; then
  echo "[entrypoint] waiting for MySQL at ${TRAVEL_NOTIFICATION_MYSQL_HOST:-mysql}:${TRAVEL_NOTIFICATION_MYSQL_PORT:-3306} ..."
  python - <<'PY'
import os
import sys
import time

import pymysql

host = os.getenv("TRAVEL_NOTIFICATION_MYSQL_HOST", "mysql")
port = int(os.getenv("TRAVEL_NOTIFICATION_MYSQL_PORT", "3306"))
user = os.getenv("TRAVEL_NOTIFICATION_MYSQL_USER", "root")
password = os.getenv("TRAVEL_NOTIFICATION_MYSQL_PASSWORD", "")
database = os.getenv("TRAVEL_NOTIFICATION_MYSQL_DATABASE", "travel_notification_system")

for attempt in range(60):
    try:
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            connect_timeout=3,
        )
        connection.close()
        print("[entrypoint] MySQL is ready")
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        if attempt % 5 == 0:
            print(f"[entrypoint] MySQL not ready ({type(exc).__name__}); retrying...")
        time.sleep(2)

print("[entrypoint] MySQL did not become ready in time", file=sys.stderr)
sys.exit(1)
PY
fi

echo "[entrypoint] applying database migrations ..."
python scripts/apply_migrations.py || {
  echo "[entrypoint] migration failed" >&2
  exit 1
}

if [ "${RUN_SCHEDULER:-true}" = "false" ]; then
  echo "[entrypoint] scheduler disabled for this process"
fi

if [ "${WORKER_MODE:-false}" = "true" ]; then
  echo "[entrypoint] starting notification worker"
  exec python -m app.worker
fi

exec uvicorn app.api.http:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-1}" \
  --proxy-headers \
  --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-*}"
