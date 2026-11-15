from __future__ import annotations

import socket
import urllib.request
from collections.abc import Iterator

import pytest


class RealNetworkBlocked(RuntimeError):
    """Raised when a test attempts a real outbound network call."""


def _blocked(*args, **kwargs):  # noqa: ANN002, ANN003
    raise RealNetworkBlocked(
        "Real network access is disabled in tests. Inject a fake provider instead."
    )


@pytest.fixture(autouse=True)
def block_real_network(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Fail closed: no unit/integration test may reach a real external service.

    We block at the socket layer so in-process ASGI test clients still work while
    any attempt to open a real TCP connection fails immediately.
    """

    monkeypatch.setattr(socket.socket, "connect", _blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    monkeypatch.setattr(urllib.request, "urlopen", _blocked)

    # Safe defaults for every test. Individual tests may override with monkeypatch.
    monkeypatch.setenv("SMS_PROVIDER", "mock")
    monkeypatch.setenv("TRAVEL_NOTIFICATION_PERSISTENCE_BACKEND", "json")
    monkeypatch.setenv("WECHAT_WEBHOOK_URL", "https://example.invalid/test-webhook")
    monkeypatch.delenv("QWEATHER_API_HOST", raising=False)
    monkeypatch.delenv("QWEATHER_API_KEY", raising=False)
    monkeypatch.delenv("GLM_API_KEY", raising=False)

    # The webhook URL is captured at import time in the provider module.
    from app.modules.integration import wechat_provider

    monkeypatch.setattr(
        wechat_provider,
        "WECHAT_WEBHOOK_URL",
        "https://example.invalid/test-webhook",
    )
    yield


@pytest.fixture
def json_store(tmp_path):
    from app.modules.integration.persistence import JsonFileStore

    return JsonFileStore(base_dir=tmp_path)


@pytest.fixture
def isolated_db_dir(tmp_path, monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("TRAVEL_NOTIFICATION_DB_DIR", str(tmp_path))
    return str(tmp_path)
