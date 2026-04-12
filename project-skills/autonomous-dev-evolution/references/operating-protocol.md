# Operating Protocol

## Goal
Improve delivery speed and reliability by preserving high-signal development memory.

## Event Types
- `user_guidance`: direct user requirement or correction.
- `user_command`: command intent before execution.
- `execution_result`: command outcome after execution.
- `reflection`: what worked, what failed, and why.
- `pattern`: reusable workflow extracted from reflections.

## Minimum Per Task
1. At least one `user_guidance` event.
2. One `user_command` and one `execution_result` for each major command.
3. One `reflection` event before task completion.
4. One playbook distillation run.

## Reuse Policy
- Start new tasks by reading `.codex-memory/self-evolution/fast_path.md`.
- Prefer command patterns with high success counts.
- Demote patterns with repeated failures.

## Safety
- Do not store tokens, passwords, private keys, or personal identifiers.
- Replace sensitive values with placeholders before logging.
