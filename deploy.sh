#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"
RUNTIME_DIR="$REPO_ROOT/.runtime"
VENV_DIR="$REPO_ROOT/.venv"

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8001}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-4180}"

BACKEND_URL="http://${BACKEND_HOST}:${BACKEND_PORT}"
FRONTEND_URL="http://${FRONTEND_HOST}:${FRONTEND_PORT}"

BACKEND_PID_FILE="$RUNTIME_DIR/backend.deploy.pid"
FRONTEND_PID_FILE="$RUNTIME_DIR/frontend.deploy.pid"
BACKEND_LOG_FILE="$RUNTIME_DIR/backend.deploy.log"
FRONTEND_LOG_FILE="$RUNTIME_DIR/frontend.deploy.log"

log() {
  echo "[deploy] $*"
}

die() {
  echo "[deploy] ERROR: $*" >&2
  exit 1
}

require_command() {
  local command_name="$1"
  command -v "$command_name" >/dev/null 2>&1 || die "缺少依赖命令: $command_name"
}

ensure_runtime_dir() {
  mkdir -p "$RUNTIME_DIR"
}

python_bin() {
  echo "$VENV_DIR/bin/python"
}

pid_is_running() {
  local pid="$1"
  kill -0 "$pid" >/dev/null 2>&1
}

read_pid() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]]; then
    tr -d '[:space:]' <"$pid_file"
  fi
}

stop_from_pid_file() {
  local pid_file="$1"
  local service_name="$2"

  if [[ ! -f "$pid_file" ]]; then
    log "${service_name} 未运行"
    return 0
  fi

  local pid
  pid="$(read_pid "$pid_file")"
  if [[ -z "$pid" ]]; then
    rm -f "$pid_file"
    log "${service_name} PID 文件为空，已清理"
    return 0
  fi

  if pid_is_running "$pid"; then
    log "停止 ${service_name} (pid=${pid})"
    kill "$pid"
    for _ in $(seq 1 20); do
      if ! pid_is_running "$pid"; then
        break
      fi
      sleep 1
    done
    if pid_is_running "$pid"; then
      log "${service_name} 未在预期时间内退出，执行强制停止"
      kill -9 "$pid"
    fi
  else
    log "${service_name} 进程不存在，清理残留 PID 文件"
  fi

  rm -f "$pid_file"
}

create_venv() {
  require_command python3
  if [[ ! -x "$(python_bin)" ]]; then
    log "创建 Python 虚拟环境 .venv"
    (cd "$REPO_ROOT" && python3 -m venv .venv)
  fi
}

install_backend() {
  create_venv
  log "安装后端依赖"
  (
    cd "$REPO_ROOT"
    "$(python_bin)" -m pip install --upgrade pip
    "$(python_bin)" -m pip install -e .
  )
}

install_frontend() {
  require_command node
  require_command npm
  log "安装前端依赖"
  (cd "$REPO_ROOT" && npm -C frontend install)
}

build_frontend() {
  log "构建前端静态资源"
  (cd "$REPO_ROOT" && npm -C frontend run build)
}

wait_for_http() {
  local url="$1"
  local label="$2"
  local max_attempts="${3:-30}"

  for _ in $(seq 1 "$max_attempts"); do
    if curl --noproxy '*' -fsS "$url" >/dev/null 2>&1; then
      log "${label} 已就绪"
      return 0
    fi
    sleep 1
  done

  return 1
}

wait_for_http_with_python_fallback() {
  local url="$1"
  local label="$2"
  local max_attempts="${3:-60}"

  for _ in $(seq 1 "$max_attempts"); do
    if curl --noproxy '*' -fsS "$url" >/dev/null 2>&1; then
      log "${label} 已就绪"
      return 0
    fi

    if "$(python_bin)" - <<PY >/dev/null 2>&1
from urllib.request import ProxyHandler, build_opener
build_opener(ProxyHandler({})).open("${url}", timeout=3).read()
PY
    then
      log "${label} 已就绪"
      return 0
    fi

    sleep 1
  done

  return 1
}

check_backend_health() {
  curl --noproxy '*' -fsS "${BACKEND_URL}/api/health" >/dev/null
}

check_frontend_login() {
  curl --noproxy '*' -fsS -X POST "${FRONTEND_URL}/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"123456"}' >/dev/null
}

start_backend() {
  ensure_runtime_dir
  local existing_pid
  existing_pid="$(read_pid "$BACKEND_PID_FILE")"
  if [[ -n "$existing_pid" ]] && pid_is_running "$existing_pid"; then
    log "backend 已运行 (pid=${existing_pid})"
    return 0
  fi

  log "启动 backend: uvicorn app.api.http:app"
  local launch_cmd
  launch_cmd="cd \"$REPO_ROOT\" && exec env PYTHONPATH=\"$REPO_ROOT/src\${PYTHONPATH:+:\${PYTHONPATH}}\" \"$(python_bin)\" -m uvicorn app.api.http:app --host \"$BACKEND_HOST\" --port \"$BACKEND_PORT\""
  if command -v setsid >/dev/null 2>&1; then
    nohup setsid bash -lc "$launch_cmd" >"$BACKEND_LOG_FILE" 2>&1 </dev/null &
  else
    nohup bash -lc "$launch_cmd" >"$BACKEND_LOG_FILE" 2>&1 </dev/null &
  fi
  echo $! >"$BACKEND_PID_FILE"
}

start_frontend() {
  ensure_runtime_dir
  local existing_pid
  existing_pid="$(read_pid "$FRONTEND_PID_FILE")"
  if [[ -n "$existing_pid" ]] && pid_is_running "$existing_pid"; then
    log "frontend proxy 已运行 (pid=${existing_pid})"
    return 0
  fi

  log "启动 frontend proxy: scripts/frontend_proxy_server.py"
  local launch_cmd
  launch_cmd="cd \"$REPO_ROOT\" && exec \"$(python_bin)\" scripts/frontend_proxy_server.py --host \"$FRONTEND_HOST\" --port \"$FRONTEND_PORT\" --backend \"$BACKEND_URL\" --static-dir frontend/dist"
  if command -v setsid >/dev/null 2>&1; then
    nohup setsid bash -lc "$launch_cmd" >"$FRONTEND_LOG_FILE" 2>&1 </dev/null &
  else
    nohup bash -lc "$launch_cmd" >"$FRONTEND_LOG_FILE" 2>&1 </dev/null &
  fi
  echo $! >"$FRONTEND_PID_FILE"
}

prepare() {
  require_command curl
  install_backend
  install_frontend
  build_frontend
}

show_status_line() {
  local pid_file="$1"
  local service_name="$2"
  local url="$3"
  local pid
  pid="$(read_pid "$pid_file")"

  if [[ -n "$pid" ]] && pid_is_running "$pid"; then
    echo "${service_name}: running (pid=${pid}) ${url}"
  else
    echo "${service_name}: stopped"
  fi
}

up() {
  prepare
  start_backend

  if ! wait_for_http_with_python_fallback "${BACKEND_URL}/api/health" "backend"; then
    tail -n 50 "$BACKEND_LOG_FILE" || true
    die "backend 启动失败，请检查 ${BACKEND_LOG_FILE}"
  fi

  start_frontend

  if ! wait_for_http_with_python_fallback "${FRONTEND_URL}" "frontend"; then
    tail -n 50 "$FRONTEND_LOG_FILE" || true
    die "frontend 启动失败，请检查 ${FRONTEND_LOG_FILE}"
  fi

  check_backend_health
  check_frontend_login

  log "一键部署完成"
  log "backend:  ${BACKEND_URL}"
  log "frontend: ${FRONTEND_URL}"
  log "日志: backend=${BACKEND_LOG_FILE} frontend=${FRONTEND_LOG_FILE}"
}

down() {
  stop_from_pid_file "$FRONTEND_PID_FILE" "frontend"
  stop_from_pid_file "$BACKEND_PID_FILE" "backend"
}

restart() {
  down
  up
}

status() {
  show_status_line "$BACKEND_PID_FILE" "backend" "${BACKEND_URL}"
  show_status_line "$FRONTEND_PID_FILE" "frontend" "${FRONTEND_URL}"
}

logs() {
  local target="${2:-all}"

  case "$target" in
    backend)
      tail -n 120 -f "$BACKEND_LOG_FILE"
      ;;
    frontend)
      tail -n 120 -f "$FRONTEND_LOG_FILE"
      ;;
    all)
      log "backend log: $BACKEND_LOG_FILE"
      tail -n 40 "$BACKEND_LOG_FILE" 2>/dev/null || true
      log "frontend log: $FRONTEND_LOG_FILE"
      tail -n 40 "$FRONTEND_LOG_FILE" 2>/dev/null || true
      ;;
    *)
      die "未知日志目标: ${target}，可选 backend|frontend|all"
      ;;
  esac
}

usage() {
  cat <<EOF
Usage:
  bash deploy.sh up
  bash deploy.sh down
  bash deploy.sh restart
  bash deploy.sh status
  bash deploy.sh logs [backend|frontend|all]

Environment overrides:
  BACKEND_HOST=${BACKEND_HOST}
  BACKEND_PORT=${BACKEND_PORT}
  FRONTEND_HOST=${FRONTEND_HOST}
  FRONTEND_PORT=${FRONTEND_PORT}
EOF
}

main() {
  local action="${1:-help}"

  case "$action" in
    up)
      up
      ;;
    down)
      down
      ;;
    restart)
      restart
      ;;
    status)
      status
      ;;
    logs)
      logs "$@"
      ;;
    help|-h|--help)
      usage
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"
