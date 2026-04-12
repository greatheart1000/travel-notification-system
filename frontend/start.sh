#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

MODE="${1:-dev}"
SKIP_API_CHECK="${2:-}"

log() {
  echo "[frontend/start] $*"
}

ensure_node() {
  if ! command -v node >/dev/null 2>&1; then
    log "未检测到 Node.js，请安装 Node.js >= 18"
    exit 1
  fi
  log "Node.js: $(node --version)"
  log "npm: $(npm --version)"
}

ensure_deps() {
  cd "$SCRIPT_DIR"
  if [[ ! -d node_modules ]]; then
    log "安装前端依赖..."
    if [[ -f package-lock.json ]]; then
      npm ci
    else
      npm install
    fi
  else
    log "前端依赖已就绪"
  fi
}

health() {
  if command -v curl >/dev/null 2>&1; then
    if curl -fsS "http://127.0.0.1:8000/api/health" >/dev/null; then
      log "后端健康检查通过: /api/health"
      return 0
    fi
  fi
  log "后端健康检查失败，请先启动 backend"
  return 1
}

run_dev() {
  ensure_node
  ensure_deps

  if [[ "$SKIP_API_CHECK" != "--skip-api-check" ]]; then
    health || true
  fi

  log "启动前端开发服务: http://127.0.0.1:5173"
  cd "$SCRIPT_DIR"
  npm run dev
}

run_smoke() {
  log "调用仓库级 smoke 校验"
  cd "$REPO_ROOT"
  python dev-server.py smoke --spawn-backend
}

usage() {
  cat <<'EOF'
Usage:
  ./start.sh dev [--skip-api-check]   启动前端开发服务
  ./start.sh health                   检查后端 /api/health
  ./start.sh smoke                    执行 API smoke（委托 dev-server.py）
EOF
}

case "$MODE" in
  dev)
    run_dev
    ;;
  health)
    health
    ;;
  smoke)
    run_smoke
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage
    exit 1
    ;;
esac
