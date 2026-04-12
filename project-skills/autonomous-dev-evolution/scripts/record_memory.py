#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import json
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

EVENT_KINDS = [
    "user_guidance",
    "user_command",
    "execution_result",
    "reflection",
    "pattern",
]


def _run_git(args: list[str], cwd: Path) -> str:
    try:
        result = subprocess.check_output(["git", *args], cwd=str(cwd), stderr=subprocess.DEVNULL)
        return result.decode("utf-8").strip()
    except Exception:
        return ""


def _repo_root() -> Path:
    cwd = Path.cwd()
    root = _run_git(["rev-parse", "--show-toplevel"], cwd)
    if root:
        return Path(root)
    return cwd


def _now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _parse_tags(tags: str) -> list[str]:
    if not tags:
        return []
    return [token.strip() for token in tags.split(",") if token.strip()]


def _parse_meta(meta_raw: str) -> dict[str, Any]:
    if not meta_raw:
        return {}
    parsed = json.loads(meta_raw)
    if not isinstance(parsed, dict):
        raise ValueError("--meta-json must be a JSON object")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description="Append one self-evolution event to memory log")
    parser.add_argument("--kind", required=True, choices=EVENT_KINDS)
    parser.add_argument("--content", required=True)
    parser.add_argument("--command", default="")
    parser.add_argument("--status", choices=["success", "failed", "unknown"], default="unknown")
    parser.add_argument("--task-id", default="")
    parser.add_argument("--tags", default="")
    parser.add_argument("--meta-json", default="")
    parser.add_argument("--log-path", default=".codex-memory/self-evolution/events.ndjson")
    args = parser.parse_args()

    root = _repo_root()
    log_path = (root / args.log_path).resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    event = {
        "id": str(uuid.uuid4()),
        "timestamp_utc": _now_utc(),
        "kind": args.kind,
        "content": args.content,
        "command": args.command,
        "status": args.status,
        "task_id": args.task_id,
        "tags": _parse_tags(args.tags),
        "branch": _run_git(["rev-parse", "--abbrev-ref", "HEAD"], root),
        "commit": _run_git(["rev-parse", "HEAD"], root),
        "author": getpass.getuser(),
        "meta": _parse_meta(args.meta_json),
    }

    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=True) + "\n")

    print(
        json.dumps(
            {"ok": True, "log_path": str(log_path), "event_id": event["id"]}, ensure_ascii=True
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
