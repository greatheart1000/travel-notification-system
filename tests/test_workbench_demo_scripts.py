from __future__ import annotations

from scripts import verify_workbench_routes


class _FakeResponse:
    status = 200

    def __init__(self, content: bytes) -> None:
        self._content = content

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, size: int = -1) -> bytes:
        if size == -1:
            return self._content
        return self._content[:size]


class _FakeOpener:
    def __init__(self, content: str) -> None:
        self._content = content.encode("utf-8")

    def open(self, _req: object, timeout: int = 15) -> _FakeResponse:
        return _FakeResponse(self._content)


def test_http_status_reads_enough_html_to_find_vite_root(monkeypatch) -> None:
    prefix = "<!doctype html><html><head>" + (" " * 600) + "</head><body>"
    html = prefix + '<div id="root"></div><script type="module" src="/src/App.tsx"></script>'
    monkeypatch.setattr(verify_workbench_routes, "URL_OPENER", _FakeOpener(html))

    status, content = verify_workbench_routes.http_status("http://127.0.0.1:5173/dashboard")

    assert status == 200
    assert '<div id="root"' in content
