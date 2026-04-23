#!/usr/bin/env bash
set -euo pipefail

BASE_URL="http://127.0.0.1:8001"
FRONTEND_URL="http://127.0.0.1:5173"
USERNAME="admin"
PASSWORD="123456"
KEEP_RUNNING="true"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url)
      BASE_URL="$2"
      shift 2
      ;;
    --frontend-url)
      FRONTEND_URL="$2"
      shift 2
      ;;
    --username)
      USERNAME="$2"
      shift 2
      ;;
    --password)
      PASSWORD="$2"
      shift 2
      ;;
    --no-keep)
      KEEP_RUNNING="false"
      shift
      ;;
    *)
      echo "Unknown arg: $1"
      echo "Usage: scripts/run_workbench_demo.sh [--base-url URL] [--frontend-url URL] [--username USER] [--password PWD] [--no-keep]"
      exit 1
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_DIR="$REPO_ROOT/frontend"
FRONTEND_HOSTPORT="${FRONTEND_URL#http://}"
FRONTEND_HOST="${FRONTEND_HOSTPORT%%:*}"
FRONTEND_PORT="${FRONTEND_HOSTPORT##*:}"

cleanup() {
  if [[ -n "${FRONTEND_PID:-}" ]]; then
    kill "$FRONTEND_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "[1/4] Seeding backend demo data..."
python "$REPO_ROOT/scripts/seed_frontend_workbench_demo.py" \
  --base-url "$BASE_URL" \
  --username "$USERNAME" \
  --password "$PASSWORD"

echo "[2/4] Starting frontend in real-data mode..."
(
  cd "$FRONTEND_DIR"
  VITE_API_BASE_URL="$BASE_URL" VITE_WORKBENCH_DATA_MODE=real npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT" > /tmp/workbench-frontend.log 2>&1
) &
FRONTEND_PID=$!

echo "[3/4] Waiting frontend server..."
for _ in {1..30}; do
  if python - <<PY
from urllib import request
try:
    request.build_opener(request.ProxyHandler({})).open("$FRONTEND_URL/dashboard", timeout=2)
    print("ok")
except Exception:
    raise SystemExit(1)
PY
  then
    break
  fi
  sleep 1
done

echo "[4/4] Verifying backend + required routes..."
python "$REPO_ROOT/scripts/verify_workbench_routes.py" \
  --backend-url "$BASE_URL" \
  --frontend-url "$FRONTEND_URL" \
  --username "$USERNAME" \
  --password "$PASSWORD"

printf "\n✅ All checks passed.\n"
echo "Frontend log: /tmp/workbench-frontend.log"

if [[ "$KEEP_RUNNING" == "true" ]]; then
  echo "Frontend dev server is running (PID=$FRONTEND_PID)."
  echo "Open: $FRONTEND_URL/dashboard"
  echo "Press Ctrl+C to stop."
  wait "$FRONTEND_PID"
fi
