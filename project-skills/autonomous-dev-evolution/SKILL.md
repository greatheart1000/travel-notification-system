---
name: autonomous-dev-evolution
description: Capture every user instruction and command execution into structured local memory, then distill reusable fast-path playbooks to speed up future development in this repository. Use when the user requests continuous learning, memory-driven iteration, command history learning, autonomous improvement loops, or self-evolution behavior.
---

# Autonomous Dev Evolution Skill

## Purpose
Create a practical self-improvement loop for Codex at repository level.
Learning is implemented through local memory artifacts, not model-weight changes.

## Mandatory Loop
1. Record user guidance immediately.
2. Execute shell work through the memory wrapper.
3. Record command outcomes (success or failure).
4. Distill memory into a fast-path playbook at the end of each task.
5. Reuse distilled patterns in the next task.

## Scripts
- `scripts/record_memory.py`
  - Append one structured event to `.codex-memory/self-evolution/events.ndjson`.
- `scripts/run_with_memory.sh`
  - Execute one command and automatically log command + result.
- `scripts/distill_playbook.py`
  - Convert event history into:
    - `.codex-memory/self-evolution/fast_path.md`
    - `.codex-memory/self-evolution/metrics.json`
- `scripts/migrate_cross_project_memory.py`
  - `sync-global`: sync project memory to user-level global memory (`~/.codex-memory/global-self-evolution`)
  - `bootstrap-project`: seed a new project with global high-value patterns

## Standard Usage
- Record user instruction:
```bash
python project-skills/autonomous-dev-evolution/scripts/record_memory.py \
  --kind user_guidance \
  --content "User asked to optimize trigger fallback logic" \
  --task-id task-2026-04-11-01 \
  --tags trigger,notification
```

- Run command with automatic memory logging:
```bash
project-skills/autonomous-dev-evolution/scripts/run_with_memory.sh \
  --task-id task-2026-04-11-01 \
  -- python -m pytest -q
```

- Distill latest playbook:
```bash
python project-skills/autonomous-dev-evolution/scripts/distill_playbook.py
```

- Sync current project memory into user-level global scope:
```bash
python project-skills/autonomous-dev-evolution/scripts/migrate_cross_project_memory.py \
  sync-global
```

- Seed a new project template from global memory:
```bash
python project-skills/autonomous-dev-evolution/scripts/migrate_cross_project_memory.py \
  bootstrap-project \
  --target-root /path/to/new-project
```

## Quality Rules
- Keep logs append-only.
- Keep UTC timestamps.
- Record both successful and failed attempts.
- Distill after each meaningful implementation cycle.
- Never log secrets or raw credentials.

## References
- `references/operating-protocol.md`
