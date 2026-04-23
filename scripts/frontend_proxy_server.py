#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


def build_backend_opener():
    return build_opener(ProxyHandler({}))


BACKEND_OPENER = build_backend_opener()


class FrontendProxyHandler(SimpleHTTPRequestHandler):
    backend_base: str = "http://127.0.0.1:18000"
    static_dir: str = "frontend/dist"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=self.static_dir, **kwargs)

    def _is_api(self) -> bool:
        return self.path.startswith("/api/")

    def _proxy_api(self) -> None:
        target = f"{self.backend_base.rstrip('/')}{self.path}"
        content_length = int(self.headers.get("Content-Length", "0") or 0)
        body = self.rfile.read(content_length) if content_length > 0 else None

        forward_headers = {
            k: v
            for k, v in self.headers.items()
            if k.lower() not in HOP_BY_HOP_HEADERS and k.lower() != "host"
        }

        req = Request(target, data=body, headers=forward_headers, method=self.command)
        try:
            with BACKEND_OPENER.open(req, timeout=30) as resp:
                resp_body = resp.read()
                self.send_response(resp.status)
                for key, value in resp.getheaders():
                    if key.lower() in HOP_BY_HOP_HEADERS:
                        continue
                    self.send_header(key, value)
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(resp_body)
        except HTTPError as err:
            err_body = err.read()
            self.send_response(err.code)
            for key, value in err.headers.items():
                if key.lower() in HOP_BY_HOP_HEADERS:
                    continue
                self.send_header(key, value)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(err_body)
        except URLError:
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(b'{"code":502,"error":"backend_unreachable"}')

    def do_GET(self) -> None:  # noqa: N802
        if self._is_api():
            self._proxy_api()
            return

        path = self.translate_path(self.path)
        if self.path != "/" and not os.path.exists(path):
            self.path = "/index.html"
        super().do_GET()

    def do_HEAD(self) -> None:  # noqa: N802
        if self._is_api():
            self._proxy_api()
            return
        super().do_HEAD()

    def do_POST(self) -> None:  # noqa: N802
        if self._is_api():
            self._proxy_api()
            return
        self.send_error(405, "Method Not Allowed")

    def do_PUT(self) -> None:  # noqa: N802
        if self._is_api():
            self._proxy_api()
            return
        self.send_error(405, "Method Not Allowed")

    def do_DELETE(self) -> None:  # noqa: N802
        if self._is_api():
            self._proxy_api()
            return
        self.send_error(405, "Method Not Allowed")

    def do_PATCH(self) -> None:  # noqa: N802
        if self._is_api():
            self._proxy_api()
            return
        self.send_error(405, "Method Not Allowed")

    def do_OPTIONS(self) -> None:  # noqa: N802
        if self._is_api():
            self._proxy_api()
            return
        self.send_response(204)
        self.end_headers()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Serve frontend static files and proxy /api to backend"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4173)
    parser.add_argument("--backend", default="http://127.0.0.1:18000")
    parser.add_argument("--static-dir", default="frontend/dist")
    args = parser.parse_args()

    FrontendProxyHandler.backend_base = args.backend
    FrontendProxyHandler.static_dir = args.static_dir

    server = ThreadingHTTPServer((args.host, args.port), FrontendProxyHandler)
    print(f"Frontend proxy running at http://{args.host}:{args.port}, backend={args.backend}")
    server.serve_forever()


if __name__ == "__main__":
    main()
