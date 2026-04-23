#!/usr/bin/env python3
"""Verify backend APIs and frontend routes for Workbench demo."""

from __future__ import annotations

import argparse
import json
from urllib import request


def http_json(method: str, url: str, token: str | None = None, payload: dict | None = None) -> dict:
    body = None
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
    req = request.Request(url, method=method, headers=headers, data=body)
    with request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_status(url: str) -> tuple[int, str]:
    req = request.Request(url, method="GET")
    with request.urlopen(req, timeout=15) as resp:
        content = resp.read(300).decode("utf-8", errors="ignore")
        return resp.status, content


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend-url", default="http://127.0.0.1:8000")
    parser.add_argument("--frontend-url", default="http://127.0.0.1:5173")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="123456")
    args = parser.parse_args()

    login = http_json(
        "POST",
        f"{args.backend_url}/api/auth/login",
        payload={"username": args.username, "password": args.password},
    )
    token = str(login["data"]["access_token"])

    overview = http_json("GET", f"{args.backend_url}/api/workbench/today/overview?owner_scope=all", token=token)
    action_items = http_json("GET", f"{args.backend_url}/api/workbench/today/action-items?limit=10&owner_scope=all", token=token)
    trip_rows = http_json("GET", f"{args.backend_url}/api/trips/execution?owner_scope=all", token=token)

    items = action_items.get("data", {}).get("items", [])
    rows = trip_rows.get("data", {}).get("items", [])
    if not items:
        raise SystemExit("❌ workbench action-items is empty; please run seeding first")
    if not rows:
        raise SystemExit("❌ trips execution rows is empty; please run seeding first")

    task_id = str(items[0].get("id") or "")
    group_id = str(rows[0].get("trip_id") or "")
    if not task_id or not group_id:
        raise SystemExit("❌ cannot resolve dynamic task/group id")

    print("✅ Backend verification")
    print(f"  - pending_tasks={overview.get('data', {}).get('pending_tasks')}")
    print(f"  - sample task_id={task_id}")
    print(f"  - sample group_id={group_id}")

    routes = [
        "/dashboard",
        "/tasks/todo",
        "/tasks/overdue",
        "/tasks/takeover",
        "/groups/high-risk",
        f"/tasks/{task_id}",
        f"/groups/high-risk/{group_id}",
    ]

    print("✅ Frontend route verification")
    for route in routes:
        status, content = http_status(f"{args.frontend_url}{route}")
        if status != 200:
            raise SystemExit(f"❌ {route} -> HTTP {status}")
        if "<div id=\"root\"" not in content:
            raise SystemExit(f"❌ {route} -> unexpected HTML content")
        print(f"  - {route} -> HTTP 200")

    print("\n🎉 Workbench routes are ready for manual UI checks.")


if __name__ == "__main__":
    main()
