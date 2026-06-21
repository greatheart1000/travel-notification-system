#!/usr/bin/env python3
"""高性能静态文件服务器 — 缓存头 + SPA fallback + API 代理."""
from http.server import SimpleHTTPRequestHandler, HTTPServer
import os
import urllib.request
import json

DIST = os.path.join(os.path.dirname(__file__), 'dist')
API_TARGET = os.environ.get('API_TARGET', 'http://127.0.0.1:3001')
CACHE_AGES = {
    '.js': 31536000, '.css': 31536000, '.woff2': 31536000,
    '.png': 86400, '.svg': 86400, '.ico': 86400,
}

class SPAHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIST, **kwargs)

    def end_headers(self):
        ext = os.path.splitext(self.path)[1].lower()
        max_age = CACHE_AGES.get(ext, 0)
        if max_age > 0:
            self.send_header('Cache-Control', f'public, max-age={max_age}, immutable')
        else:
            self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def do_GET(self):
        # 代理 /api/* 请求到后端
        if self.path.startswith('/api/'):
            self._proxy_to_backend('GET')
            return
        path = self.path.split('?')[0]
        if not os.path.splitext(path)[1] and path != '/':
            file_path = os.path.join(DIST, path.lstrip('/'))
            if not os.path.exists(file_path) and not os.path.exists(file_path + '.html'):
                self.path = '/index.html'
        super().do_GET()

    def do_POST(self):
        if self.path.startswith('/api/'):
            self._proxy_to_backend('POST')
            return
        self.send_error(404)

    def do_PUT(self):
        if self.path.startswith('/api/'):
            self._proxy_to_backend('PUT')
            return
        self.send_error(404)

    def do_DELETE(self):
        if self.path.startswith('/api/'):
            self._proxy_to_backend('DELETE')
            return
        self.send_error(404)

    def _proxy_to_backend(self, method: str):
        target_url = API_TARGET + self.path
        if self.headers.get('Content-Length'):
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
        else:
            body = None

        req = urllib.request.Request(target_url, data=body, method=method)
        for key in ['Content-Type', 'Authorization', 'Accept']:
            val = self.headers.get(key)
            if val:
                req.add_header(key, val)

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
                self.send_response(resp.status)
                for k, v in resp.getheaders():
                    if k.lower() not in ('transfer-encoding', 'connection', 'server', 'date'):
                        self.send_header(k, v)
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.end_headers()
            self.wfile.write(e.read() or b'')
        except Exception as e:
            self.send_error(502, f'API proxy error: {e}')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5173))
    server = HTTPServer(('0.0.0.0', port), SPAHandler)
    print(f'Frontend: http://0.0.0.0:{port}  → API: {API_TARGET}')
    server.serve_forever()
