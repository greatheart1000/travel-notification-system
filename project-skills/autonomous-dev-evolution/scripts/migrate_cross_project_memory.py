#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def _load_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict):
                events.append(event)
    return events


def _append_events(path: Path, events: list[dict[str, Any]]) -> None:
    if not events:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event, ensure_ascii=True) + "\n")


def _repo_name_from_path(path: Path) -> str:
    return path.resolve().name or "unknown-repo"


def _event_id_set(events: list[dict[str, Any]]) -> set[str]:
    ids: set[str] = set()
    for event in events:
        event_id = str(event.get("id") or "").strip()
        if event_id:
            ids.add(event_id)
    return ids


def _build_command_patterns(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {"attempts": 0, "success": 0, "failed": 0, "unknown": 0}
    )
    for event in events:
        if event.get("kind") != "execution_result":
            continue
        command = str(event.get("command") or "").strip()
        if not command:
            continue
        status = str(event.get("status") or "unknown").strip().lower()
        if status not in {"success", "failed", "unknown"}:
            status = "unknown"
        stats[command]["attempts"] += 1
        stats[command][status] += 1

    ranked: list[dict[str, Any]] = []
    for command, value in stats.items():
        attempts = value["attempts"]
        success = value["success"]
        failed = value["failed"]
        success_rate = (success / attempts) if attempts else 0.0
        # score favors reliability first, then evidence volume
        score = success_rate * math.log2(attempts + 1)
        ranked.append(
            {
                "command": command,
                "attempts": attempts,
                "success": success,
                "failed": failed,
                "unknown": value["unknown"],
                "success_rate": round(success_rate, 4),
                "score": round(score, 4),
            }
        )

    ranked.sort(
        key=lambda item: (item["score"], item["success_rate"], item["attempts"], -item["failed"]),
        reverse=True,
    )
    return ranked


def _recent_unique_contents(events: list[dict[str, Any]], kinds: set[str], limit: int) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for event in reversed(events):
        if event.get("kind") not in kinds:
            continue
        content = str(event.get("content") or "").strip()
        if not content or content in seen:
            continue
        seen.add(content)
        result.append(content)
        if len(result) >= limit:
            break
    result.reverse()
    return result


def _write_global_fast_path(global_root: Path, profile: dict[str, Any]) -> Path:
    out = global_root / "fast_path.global.md"
    top_patterns: list[dict[str, Any]] = profile.get("top_command_patterns", [])
    recent_reflections: list[str] = profile.get("recent_reflections", [])
    recent_guidance: list[str] = profile.get("recent_user_guidance", [])

    lines = [
        "# Global Self-Evolution Fast Path",
        "",
        f"Generated (UTC): {profile.get('generated_at_utc', _now_utc())}",
        "",
        "## Top Command Patterns",
    ]
    if not top_patterns:
        lines.append("- No command patterns yet.")
    else:
        for item in top_patterns[:12]:
            lines.append(
                "- "
                + f"`{item['command']}` | attempts={item['attempts']} "
                + f"success={item['success']} failed={item['failed']} "
                + f"rate={item['success_rate']}"
            )

    lines.extend(["", "## Recent User Guidance"])
    if not recent_guidance:
        lines.append("- No guidance yet.")
    else:
        for content in recent_guidance:
            lines.append(f"- {content}")

    lines.extend(["", "## Recent Reflections"])
    if not recent_reflections:
        lines.append("- No reflections yet.")
    else:
        for content in recent_reflections:
            lines.append(f"- {content}")

    lines.extend(
        [
            "",
            "## Cross-Project Usage",
            "- In a new project, run bootstrap-project to seed local memory.",
            "- Keep project-specific decisions local; only reuse stable execution patterns.",
        ]
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def sync_global(source_root: Path, global_root: Path, top_n: int) -> dict[str, Any]:
    source_events_path = source_root / ".codex-memory/self-evolution/events.ndjson"
    source_events = _load_events(source_events_path)

    global_events_path = global_root / "events.ndjson"
    global_events = _load_events(global_events_path)
    existing_ids = _event_id_set(global_events)

    new_events: list[dict[str, Any]] = []
    now = _now_utc()
    for event in source_events:
        event_id = str(event.get("id") or "").strip()
        if not event_id or event_id in existing_ids:
            continue
        merged = dict(event)
        meta = merged.get("meta")
        if not isinstance(meta, dict):
            meta = {}
        meta = dict(meta)
        meta["source_repo_root"] = str(source_root.resolve())
        meta["source_repo_name"] = _repo_name_from_path(source_root)
        meta["synced_to_user_scope_utc"] = now
        merged["meta"] = meta
        new_events.append(merged)
        existing_ids.add(event_id)

    _append_events(global_events_path, new_events)
    all_events = global_events + new_events

    by_kind = Counter(str(event.get("kind") or "unknown") for event in all_events)
    patterns = _build_command_patterns(all_events)
    profile = {
        "generated_at_utc": now,
        "global_event_count": len(all_events),
        "events_by_kind": dict(by_kind),
        "top_command_patterns": patterns[: max(top_n, 1)],
        "recent_user_guidance": _recent_unique_contents(all_events, {"user_guidance"}, 20),
        "recent_reflections": _recent_unique_contents(all_events, {"reflection", "pattern"}, 20),
    }

    profile_path = global_root / "high_value_patterns.json"
    _write_json(profile_path, profile)
    fast_path = _write_global_fast_path(global_root, profile)

    catalog_path = global_root / "catalog.json"
    catalog = _read_json(catalog_path)
    repos = catalog.get("repos")
    if not isinstance(repos, dict):
        repos = {}
    repo_key = str(source_root.resolve())
    repos[repo_key] = {
        "repo_name": _repo_name_from_path(source_root),
        "last_sync_utc": now,
        "source_event_count": len(source_events),
        "new_events_synced": len(new_events),
    }
    catalog["repos"] = repos
    catalog["updated_at_utc"] = now
    _write_json(catalog_path, catalog)

    return {
        "ok": True,
        "source_events": len(source_events),
        "new_events_synced": len(new_events),
        "global_events": len(all_events),
        "global_root": str(global_root.resolve()),
        "profile_path": str(profile_path.resolve()),
        "fast_path": str(fast_path.resolve()),
    }


def bootstrap_project(target_root: Path, global_root: Path, top_n: int) -> dict[str, Any]:
    profile_path = global_root / "high_value_patterns.json"
    profile = _read_json(profile_path)
    if not profile:
        raise FileNotFoundError(
            f"Global profile not found at {profile_path}. Run sync-global first."
        )

    target_memory = target_root / ".codex-memory/self-evolution"
    target_memory.mkdir(parents=True, exist_ok=True)

    patterns = profile.get("top_command_patterns")
    if not isinstance(patterns, list):
        patterns = []
    selected = patterns[: max(top_n, 1)]

    seed_payload = {
        "generated_at_utc": _now_utc(),
        "source_global_root": str(global_root.resolve()),
        "source_profile_path": str(profile_path.resolve()),
        "top_command_patterns": selected,
        "recent_user_guidance": profile.get("recent_user_guidance", []),
        "recent_reflections": profile.get("recent_reflections", []),
    }
    seed_json = target_memory / "bootstrap_patterns.json"
    _write_json(seed_json, seed_payload)

    seed_md = target_memory / "global_seed_fast_path.md"
    lines = [
        "# Global Seed Fast Path",
        "",
        f"Seeded (UTC): {seed_payload['generated_at_utc']}",
        "",
        "## Imported Command Patterns",
    ]
    if not selected:
        lines.append("- No imported patterns.")
    else:
        for item in selected:
            lines.append(
                "- "
                + f"`{item.get('command', '')}` | attempts={item.get('attempts', 0)} "
                + f"success_rate={item.get('success_rate', 0)}"
            )
    lines.extend(
        [
            "",
            "## Notes",
            "- This is a starting point for new projects, not a strict policy.",
            "- Re-validate commands against each new repository context.",
        ]
    )
    seed_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    events_path = target_memory / "events.ndjson"
    imported_events: list[dict[str, Any]] = []
    now = _now_utc()
    for index, item in enumerate(selected, start=1):
        cmd = str(item.get("command") or "").strip()
        if not cmd:
            continue
        imported_events.append(
            {
                "id": f"bootstrap-pattern-{now}-{index}",
                "timestamp_utc": now,
                "kind": "pattern",
                "content": f"Imported global pattern: {cmd}",
                "command": cmd,
                "status": "unknown",
                "task_id": "bootstrap-global-memory",
                "tags": ["global_seed", "cross_project"],
                "branch": "",
                "commit": "",
                "author": "memory-migration-script",
                "meta": {
                    "source": "global-self-evolution",
                    "success_rate": item.get("success_rate", 0),
                    "attempts": item.get("attempts", 0),
                },
            }
        )
    _append_events(events_path, imported_events)

    return {
        "ok": True,
        "target_root": str(target_root.resolve()),
        "seed_json": str(seed_json.resolve()),
        "seed_md": str(seed_md.resolve()),
        "seeded_pattern_events": len(imported_events),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migrate self-evolution memory across projects (project scope <-> user scope)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync_parser = subparsers.add_parser(
        "sync-global", help="Sync current project memory into user-level global memory"
    )
    sync_parser.add_argument("--source-root", default=".")
    sync_parser.add_argument(
        "--global-root",
        default=str((Path.home() / ".codex-memory/global-self-evolution").resolve()),
    )
    sync_parser.add_argument("--top-n", type=int, default=20)

    bootstrap_parser = subparsers.add_parser(
        "bootstrap-project", help="Seed a new project with global high-value memory patterns"
    )
    bootstrap_parser.add_argument("--target-root", required=True)
    bootstrap_parser.add_argument(
        "--global-root",
        default=str((Path.home() / ".codex-memory/global-self-evolution").resolve()),
    )
    bootstrap_parser.add_argument("--top-n", type=int, default=10)

    args = parser.parse_args()

    if args.command == "sync-global":
        result = sync_global(
            source_root=Path(args.source_root).resolve(),
            global_root=Path(args.global_root).resolve(),
            top_n=int(args.top_n),
        )
    else:
        result = bootstrap_project(
            target_root=Path(args.target_root).resolve(),
            global_root=Path(args.global_root).resolve(),
            top_n=int(args.top_n),
        )

    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
