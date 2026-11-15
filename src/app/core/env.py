from __future__ import annotations

import os
from pathlib import Path


def load_env_file(path: str | Path = ".env", *, override: bool = False) -> int:
    """Minimal .env loader used by local server runs and migrations.

    Docker deployments should prefer ``env_file``/real environment variables.
    Existing environment variables win unless ``override=True``.
    """
    env_path = Path(path)
    if not env_path.is_file():
        return 0
    loaded = 0
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if value and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if not key:
            continue
        if override or key not in os.environ:
            os.environ[key] = value
            loaded += 1
    return loaded


def load_dotenv_if_present() -> int:
    return load_env_file(Path.cwd() / ".env")
