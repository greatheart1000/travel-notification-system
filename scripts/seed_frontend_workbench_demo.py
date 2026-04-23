#!/usr/bin/env python3
"""Seed demo trips so Travel Hub workbench pages can show real backend data.

Usage:
  python scripts/seed_frontend_workbench_demo.py --base-url http://127.0.0.1:8000 --username admin --password 123456
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta
import json
from typing import Any
from urllib import parse, request


def http_json(method: str, url: str, payload: dict[str, Any] | None = None, token: str | None = None) -> dict[str, Any]:
    body = None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    req = request.Request(url, method=method, data=body, headers=headers)
    with request.urlopen(req, timeout=15) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw)


def login(base_url: str, username: str, password: str) -> str:
    payload = http_json(
        "POST",
        f"{base_url}/api/auth/login",
        payload={"username": username, "password": password},
    )
    return str(payload["data"]["access_token"])


def create_trip(base_url: str, token: str, payload: dict[str, object]) -> str:
    data = http_json("POST", f"{base_url}/api/trips", payload=payload, token=token)["data"]
    if isinstance(data, dict):
        return str(data.get("id") or data.get("trip", {}).get("id") or "")
    return ""


def ensure_workbench_tasks(base_url: str, token: str) -> None:
    query = parse.urlencode({"owner_scope": "all"})
    http_json("GET", f"{base_url}/api/workbench/today/overview?{query}", token=token)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="123456")
    args = parser.parse_args()

    token = login(args.base_url, args.username, args.password)
    today = date.today()

    seed_payloads = [
        {
            "destination": "新疆·喀纳斯",
            "team": "team-north-xj",
            "start_date": str(today + timedelta(days=2)),
            "end_date": str(today + timedelta(days=7)),
            "participants": 3,
            "status": "upcoming",
            "leader_name": "张导",
            "contact_phone": "13800001111",
        },
        {
            "destination": "新疆·伊犁",
            "team": "team-ili",
            "start_date": str(today + timedelta(days=1)),
            "end_date": str(today + timedelta(days=5)),
            "participants": 2,
            "status": "active",
            "leader_name": "马导",
            "contact_phone": "13800002222",
        },
        {
            "destination": "新疆·喀什",
            "team": "team-kashi",
            "start_date": str(today + timedelta(days=3)),
            "end_date": str(today + timedelta(days=6)),
            "participants": 3,
            "status": "upcoming",
            "leader_name": "刘导",
            "contact_phone": "13800003333",
        },
    ]

    created = [create_trip(args.base_url, token, payload) for payload in seed_payloads]
    ensure_workbench_tasks(args.base_url, token)

    print("Seed completed.")
    print(f"Created trips: {created}")
    print("Now open frontend /dashboard to view real backend-driven workbench data.")


if __name__ == "__main__":
    main()
