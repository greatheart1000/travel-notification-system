from __future__ import annotations

from urllib.request import ProxyHandler

from scripts.frontend_proxy_server import build_backend_opener


def test_build_backend_opener_disables_environment_proxies() -> None:
    opener = build_backend_opener()

    proxy_handlers = [handler for handler in opener.handlers if isinstance(handler, ProxyHandler)]

    assert proxy_handlers == []
