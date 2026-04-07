# Repository Guidelines

## Project Structure & Module Organization
- Core backend code is under `src/app` using a modular layout.
- `src/app/core/` contains shared domain primitives (enums, base dataclasses, event models).
- `src/app/modules/` contains business modules: `notification`, `trigger`, `complaint`, `survey`, `integration`, and `audit`.
- `src/app/main.py` provides the current MVP bootstrap/demo entry point.
- Tests live in `tests/` (currently `tests/test_bootstrap.py`).
- Product and requirement notes are in `docs/`.

## Build, Test, and Development Commands
- Create env (recommended): `python -m venv .venv && source .venv/bin/activate`
- Install project in editable mode: `python -m pip install -e .`
- Run demo flow locally: `PYTHONPATH=src python -m app.main`
- Run tests: `python -m pytest -q`

There is no separate build artifact pipeline yet; this repository is currently an MVP backend skeleton.

## Coding Style & Naming Conventions
- Target Python `>=3.11` (see `pyproject.toml`).
- Follow PEP 8 with 4-space indentation and explicit type hints for new/changed functions.
- Keep module boundaries clear: put domain data in `models.py`, behavior in `service.py` or `engine.py`.
- Use `snake_case` for files/functions/variables, `PascalCase` for classes, and `UPPER_SNAKE_CASE` for constants/enum members.
- Prefer small, composable dataclasses and explicit return structures (`dict`/typed models).

## Testing Guidelines
- Framework: `pytest` with `src` on `PYTHONPATH` via project config.
- Name test files `test_*.py` and test functions `test_<behavior>()`.
- Add/update tests with every behavior change, especially for trigger evaluation and notification fallback logic.
- Keep tests deterministic and free of network/external API calls.

## Commit & Pull Request Guidelines
- Follow Conventional Commit style used in history, e.g. `feat: add weather risk trigger filter`.
- Keep commits focused and logically grouped; avoid mixing refactor and feature work in one commit.
- PRs should include:
  - What changed and why.
  - Test evidence (command + result, e.g. `python -m pytest -q`).
  - Linked issue/task ID if available.
  - Updated docs when behavior or contracts change.
