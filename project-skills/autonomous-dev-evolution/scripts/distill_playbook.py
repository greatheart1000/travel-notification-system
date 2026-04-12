#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_events(log_path: Path) -> list[dict[str, Any]]:
    if not log_path.exists():
        return []
    events: list[dict[str, Any]] = []
    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
                if isinstance(payload, dict):
                    events.append(payload)
            except json.JSONDecodeError:
                continue
    return events


def _build_metrics(events: list[dict[str, Any]]) -> dict[str, Any]:
    kind_counter = Counter(event.get("kind", "unknown") for event in events)
    command_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {"success": 0, "failed": 0, "unknown": 0}
    )

    for event in events:
        if event.get("kind") != "execution_result":
            continue
        command = (event.get("command") or "").strip()
        if not command:
            continue
        status = event.get("status", "unknown")
        if status not in {"success", "failed", "unknown"}:
            status = "unknown"
        command_stats[command][status] += 1

    ranked = []
    for command, stats in command_stats.items():
        attempts = stats["success"] + stats["failed"] + stats["unknown"]
        success_rate = (stats["success"] / attempts) if attempts else 0.0
        ranked.append(
            {
                "command": command,
                "attempts": attempts,
                "success": stats["success"],
                "failed": stats["failed"],
                "unknown": stats["unknown"],
                "success_rate": round(success_rate, 4),
            }
        )

    ranked.sort(
        key=lambda item: (item["success_rate"], item["success"], -item["failed"]), reverse=True
    )

    return {
        "generated_at_utc": _now_utc(),
        "total_events": len(events),
        "events_by_kind": dict(kind_counter),
        "top_command_patterns": ranked[:20],
    }


def _build_playbook(events: list[dict[str, Any]], metrics: dict[str, Any]) -> str:
    recent_guidance = [
        event.get("content", "")
        for event in events
        if event.get("kind") == "user_guidance" and event.get("content")
    ][-10:]
    recent_reflections = [
        event.get("content", "")
        for event in events
        if event.get("kind") in {"reflection", "pattern"} and event.get("content")
    ][-10:]

    lines = [
        "# Self-Evolution Fast Path",
        "",
        f"Updated (UTC): {metrics['generated_at_utc']}",
        "",
        "## Overview",
        f"- Total events: {metrics['total_events']}",
        f"- Event kinds: {json.dumps(metrics['events_by_kind'], ensure_ascii=True)}",
        "",
        "## Best Command Patterns",
    ]

    if not metrics["top_command_patterns"]:
        lines.append("- No command history yet.")
    else:
        for item in metrics["top_command_patterns"][:8]:
            lines.append(
                "- "
                + f"`{item['command']}` | attempts={item['attempts']} "
                + f"success={item['success']} failed={item['failed']} "
                + f"rate={item['success_rate']}"
            )

    lines.extend(["", "## Recent User Guidance"])
    if not recent_guidance:
        lines.append("- No user guidance logged yet.")
    else:
        for guidance in recent_guidance:
            lines.append(f"- {guidance}")

    lines.extend(["", "## Recent Reflections"])
    if not recent_reflections:
        lines.append("- No reflections logged yet.")
    else:
        for reflection in recent_reflections:
            lines.append(f"- {reflection}")

    lines.extend(
        [
            "",
            "## Next Task Checklist",
            "- Read this file before executing new work.",
            "- Reuse high-success command patterns first.",
            "- Run new commands via run_with_memory.sh.",
            "- Add one reflection before task completion.",
        ]
    )

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Distill memory events into a reusable fast-path playbook"
    )
    parser.add_argument("--log-path", default=".codex-memory/self-evolution/events.ndjson")
    parser.add_argument("--out-md", default=".codex-memory/self-evolution/fast_path.md")
    parser.add_argument("--out-json", default=".codex-memory/self-evolution/metrics.json")
    args = parser.parse_args()

    root = Path.cwd()
    log_path = (root / args.log_path).resolve()
    out_md = (root / args.out_md).resolve()
    out_json = (root / args.out_json).resolve()

    events = _load_events(log_path)
    metrics = _build_metrics(events)
    playbook = _build_playbook(events, metrics)

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)

    out_md.write_text(playbook, encoding="utf-8")
    out_json.write_text(json.dumps(metrics, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {"ok": True, "events": len(events), "out_md": str(out_md), "out_json": str(out_json)}
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
