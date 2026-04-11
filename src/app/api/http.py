from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import uuid4


@dataclass(slots=True)
class Response:
    status: int
    body: dict[str, Any]


class InMemoryStore:
    def __init__(self) -> None:
        now = datetime.now(timezone.utc)
        self.trips: dict[str, dict[str, Any]] = {
            "trip-001": {
                "id": "trip-001",
                "destination": "乌鲁木齐 - 喀什",
                "team": "TEAM-001",
                "start_date": "2026-04-15",
                "end_date": "2026-04-20",
                "participants": 28,
                "status": "进行中",
            }
        }
        self.notification_templates: dict[str, dict[str, Any]] = {
            "tpl-001": {
                "id": "tpl-001",
                "name": "每日提醒",
                "template": "{{customer_name}}，您好，明日行程请注意保暖并准时集合。",
                "channel": "短信",
                "status": "启用",
                "sent_count": 1234,
                "success_rate": "98.5%",
            }
        }
        self.notifications: list[dict[str, Any]] = [
            {
                "id": "notif-001",
                "customer_name": "张三",
                "trip": "乌鲁木齐 - 喀什",
                "channel": "短信",
                "status": "sent",
                "created_at": (now - timedelta(minutes=2)).isoformat(),
            }
        ]
        self.users: dict[str, dict[str, Any]] = {
            "admin": {
                "id": "user-001",
                "username": "admin",
                "email": "admin@travelhub.com",
                "role": "admin",
                "created_at": "2026-04-11T00:00:00Z",
                "password": "123456",
            }
        }
        self.tokens: dict[str, str] = {}


store = InMemoryStore()


def _ok(data: Any) -> Response:
    return Response(status=200, body={"code": 200, "data": data})


def _error(status: int, message: str) -> Response:
    return Response(status=status, body={"code": status, "error": message})


def _parse_json(body: str) -> dict[str, Any]:
    if not body:
        return {}
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _auth_user(headers: dict[str, str]) -> dict[str, Any] | None:
    auth = headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth.replace("Bearer ", "", 1).strip()
    username = store.tokens.get(token)
    if not username:
        return None
    return store.users.get(username)


def dispatch_request(method: str, path: str, headers: dict[str, str] | None = None, body: str = "") -> Response:
    headers = {k.lower(): v for k, v in (headers or {}).items()}
    parsed = urlparse(path)
    route = parsed.path
    query = parse_qs(parsed.query)
    payload = _parse_json(body)

    if method == "GET" and route == "/api/health":
        return _ok({"status": "ok", "time": datetime.now(timezone.utc).isoformat()})

    if method == "POST" and route == "/api/auth/login":
        user = store.users.get(payload.get("username", ""))
        if not user or user["password"] != payload.get("password", ""):
            return _error(401, "Invalid credentials")
        access_token = f"tk-{uuid4().hex}"
        refresh_token = f"rf-{uuid4().hex}"
        store.tokens[access_token] = user["username"]
        return _ok({"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "expires_in": 86400})

    if method == "POST" and route == "/api/auth/logout":
        auth = headers.get("authorization", "")
        if auth.startswith("Bearer "):
            token = auth.replace("Bearer ", "", 1).strip()
            store.tokens.pop(token, None)
        return Response(status=200, body={"code": 200})

    if method == "POST" and route == "/api/auth/refresh":
        if not payload.get("refresh_token"):
            return _error(400, "refresh_token is required")
        token = f"tk-{uuid4().hex}"
        store.tokens[token] = "admin"
        return _ok({"access_token": token, "expires_in": 86400})

    if method == "GET" and route == "/api/users/me":
        user = _auth_user(headers)
        if not user:
            return _error(401, "Invalid token")
        return _ok({k: v for k, v in user.items() if k != "password"})

    if method == "GET" and route == "/api/dashboard/stats":
        sent = sum(1 for item in store.notifications if item["status"] == "sent")
        total = len(store.notifications)
        return _ok({
            "today_notifications": total,
            "active_trips": len([t for t in store.trips.values() if t["status"] != "已完成"]),
            "total_users": len(store.users),
            "pending_complaints": 12,
            "notification_success_rate": round((sent / total) * 100, 1) if total else 0.0,
        })

    if method == "GET" and route == "/api/trips":
        return _ok({"total": len(store.trips), "items": list(store.trips.values())})

    if method == "POST" and route == "/api/trips":
        for required in ["destination", "team", "start_date", "end_date"]:
            if not payload.get(required):
                return _error(400, f"Missing required field: {required}")
        trip_id = f"trip-{uuid4().hex[:8]}"
        trip = {
            "id": trip_id,
            "destination": payload["destination"],
            "team": payload["team"],
            "start_date": payload["start_date"],
            "end_date": payload["end_date"],
            "participants": int(payload.get("participants", 0)),
            "status": payload.get("status", "计划中"),
        }
        store.trips[trip_id] = trip
        return _ok(trip)

    if route.startswith("/api/trips/"):
        trip_id = route.replace("/api/trips/", "", 1)
        if trip_id not in store.trips:
            return _error(404, "Trip not found")
        if method == "PUT":
            store.trips[trip_id].update(payload)
            return _ok(store.trips[trip_id])
        if method == "DELETE":
            del store.trips[trip_id]
            return Response(status=200, body={"code": 200})

    if method == "GET" and route == "/api/notifications/templates":
        return _ok({"total": len(store.notification_templates), "items": list(store.notification_templates.values())})

    if method == "POST" and route == "/api/notifications/send":
        template_id = payload.get("template_id")
        if template_id and template_id not in store.notification_templates:
            return _error(404, "Template not found")
        record = {
            "id": f"notif-{uuid4().hex[:8]}",
            "customer_name": payload.get("customer_name", "匿名用户"),
            "trip": payload.get("trip", "未指定行程"),
            "channel": payload.get("channel", "短信"),
            "status": "sent",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        store.notifications.insert(0, record)
        return _ok({"ok": True, "notification_id": record["id"]})

    if method == "GET" and route == "/api/notifications/recent":
        limit_raw = query.get("limit", ["10"])[0]
        try:
            limit = max(int(limit_raw), 0)
        except ValueError:
            limit = 10
        items = store.notifications[:limit]
        return _ok({"total": len(items), "items": items})

    if method == "GET" and route == "/api/analytics/metrics":
        return _ok({
            "metrics": {
                "notification_success_rate": "98.5%",
                "avg_response_time": "1.2s",
                "wow_growth": "+15.3%",
                "user_satisfaction": "4.5/5",
            },
            "channel_performance": [
                {"name": "短信", "sent": 5234, "successful": 5156, "failed": 78, "rate": "98.5%"},
                {"name": "企业微信", "sent": 3421, "successful": 3398, "failed": 23, "rate": "99.3%"},
            ],
            "top_trips": [
                {"name": "乌鲁木齐 - 喀什", "notifications": 1234, "satisfaction": 4.6},
                {"name": "伊犁 - 塔城", "notifications": 856, "satisfaction": 4.3},
            ],
        })

    return _error(404, "Not found")


class APIRequestHandler(BaseHTTPRequestHandler):
    def _send_response(self, response: Response) -> None:
        payload = json.dumps(response.body, ensure_ascii=False).encode("utf-8")
        self.send_response(response.status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def _handle(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8") if length else ""
        headers = {key.lower(): value for key, value in self.headers.items()}
        response = dispatch_request(self.command, self.path, headers, body)
        self._send_response(response)

    def do_GET(self) -> None:  # noqa: N802
        self._handle()

    def do_POST(self) -> None:  # noqa: N802
        self._handle()

    def do_PUT(self) -> None:  # noqa: N802
        self._handle()

    def do_DELETE(self) -> None:  # noqa: N802
        self._handle()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type,Authorization")
        self.end_headers()


def run_http_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), APIRequestHandler)
    print(f"Travel Hub API running at http://{host}:{port}")
    server.serve_forever()
