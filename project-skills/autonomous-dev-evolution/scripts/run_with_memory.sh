#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RECORD_SCRIPT="$SCRIPT_DIR/record_memory.py"

TASK_ID=""
TAGS=""

usage() {
  echo "Usage: $0 [--task-id <id>] [--tags <a,b>] -- <command ...>"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --task-id)
      TASK_ID="${2:-}"
      shift 2
      ;;
    --tags)
      TAGS="${2:-}"
      shift 2
      ;;
    --)
      shift
      break
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

if [[ $# -eq 0 ]]; then
  usage
  exit 2
fi

COMMAND="$*"

python "$RECORD_SCRIPT" \
  --kind user_command \
  --content "$COMMAND" \
  --command "$COMMAND" \
  --status unknown \
  --task-id "$TASK_ID" \
  --tags "$TAGS" >/dev/null

set +e
bash -lc "$COMMAND"
EXIT_CODE=$?
set -e

if [[ $EXIT_CODE -eq 0 ]]; then
  STATUS="success"
else
  STATUS="failed"
fi

python "$RECORD_SCRIPT" \
  --kind execution_result \
  --content "exit_code=$EXIT_CODE" \
  --command "$COMMAND" \
  --status "$STATUS" \
  --task-id "$TASK_ID" \
  --tags "$TAGS" >/dev/null

exit $EXIT_CODE
