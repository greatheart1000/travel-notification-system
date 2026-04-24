#!/usr/bin/env python3
"""Seed Travel Hub demo data into real backend API (idempotent).

Usage:
  python scripts/seed_travel_demo_data.py --base-url http://127.0.0.1:8001 --username admin --password 123456
"""

from __future__ import annotations

import argparse
import json
from typing import Any
from urllib import request

URL_OPENER = request.build_opener(request.ProxyHandler({}))


def http_json(method: str, url: str, payload: dict[str, Any] | None = None, token: str | None = None) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = request.Request(url, method=method, data=data, headers=headers)
    with URL_OPENER.open(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def login(base_url: str, username: str, password: str) -> str:
    payload = http_json("POST", f"{base_url}/api/auth/login", {"username": username, "password": password})
    return str(payload["data"]["access_token"])


def list_trips(base_url: str, token: str) -> list[dict[str, Any]]:
    payload = http_json("GET", f"{base_url}/api/trips", token=token)
    data = payload.get("data", {})
    if isinstance(data, list):
        return data
    return list(data.get("items", []))


def upsert_trip(base_url: str, token: str, team_code: str, payload: dict[str, Any]) -> str:
    trips = list_trips(base_url, token)
    existing = next((item for item in trips if str(item.get("team_id") or item.get("team") or "") == team_code), None)

    if existing:
        trip_id = str(existing.get("id") or "")
        http_json("PUT", f"{base_url}/api/trips/{trip_id}", payload, token)
        return trip_id

    created = http_json("POST", f"{base_url}/api/trips", payload, token)
    data = created.get("data", {})
    if isinstance(data, dict) and "trip" in data:
        return str(data["trip"].get("id") or "")
    return str(data.get("id") or "")


def upsert_notification_config(base_url: str, token: str, trip_id: str, config: dict[str, Any]) -> None:
    http_json("PUT", f"{base_url}/api/trips/{trip_id}/notification-config", config, token)


def generate_daily_notifications(base_url: str, token: str, team_code: str, dates: list[str]) -> None:
    for date in dates:
        http_json(
            "POST",
            f"{base_url}/api/notifications/generate-daily",
            {
                "group_id": team_code,
                "date": date,
                "weather": "晴",
                "core_work": "每日固定时段提醒",
                "save_as_templates": False,
            },
            token,
        )


def build_seed_payloads() -> list[dict[str, Any]]:
    return [
        {
            "destination": "新疆-喀什",
            "team": "KASHI-0426",
            "start_date": "2026-04-26",
            "end_date": "2026-04-29",
            "participants": 3,
            "status": "进行中",
            "leader_name": "艾力",
            "contact_phone": "13600001111",
            "itinerary": [
                {"date": "2026-04-26", "transport": "航班+大巴", "route": "喀什机场 -> 古城", "hotel": "喀什古城酒店"},
                {"date": "2026-04-27", "transport": "旅游巴士", "route": "喀什 -> 白沙湖 -> 卡拉库里湖", "hotel": "塔县迎宾酒店"},
                {"date": "2026-04-28", "transport": "旅游巴士", "route": "塔县 -> 石头城 -> 喀什", "hotel": "喀什古城酒店"},
            ],
            "guests": [
                {"name": "王蕾", "phone": "13800001111", "notes": "轻微花粉过敏"},
                {"name": "陈浩", "phone": "13800001112", "notes": "早餐偏清淡"},
                {"name": "李晨", "phone": "13800001113", "notes": "需提醒补水"},
            ],
            "config": {
                "project_name": "喀什深度体验团",
                "manual_takeover_target": "值班管家A组",
                "sms_sign_name": "TravelHub",
                "sms_provider": "aliyun",
                "weather_enabled": True,
            },
        },
        {
            "destination": "新疆-伊犁",
            "team": "YILI-0424",
            "start_date": "2026-04-24",
            "end_date": "2026-04-28",
            "participants": 3,
            "status": "计划中",
            "leader_name": "阿迪力",
            "contact_phone": "13600002222",
            "itinerary": [
                {"date": "2026-04-24", "transport": "商务车", "route": "乌鲁木齐机场 -> 酒店", "hotel": "乌市中心酒店"},
                {"date": "2026-04-25", "transport": "旅游巴士", "route": "乌市 -> 赛里木湖", "hotel": "赛湖营地酒店"},
                {"date": "2026-04-26", "transport": "旅游巴士", "route": "赛湖 -> 果子沟 -> 伊宁", "hotel": "伊宁河谷酒店"},
            ],
            "guests": [
                {"name": "赵雅", "phone": "13800002221", "notes": "晕车"},
                {"name": "孙婷", "phone": "13800002222", "notes": "乳糖不耐受"},
                {"name": "周伟", "phone": "13800002223", "notes": "带儿童"},
            ],
            "config": {
                "project_name": "伊犁花海行摄团",
                "manual_takeover_target": "值班管家B组",
                "sms_sign_name": "TravelHub",
                "sms_provider": "tencent",
                "weather_enabled": True,
            },
        },
        {
            "destination": "新疆-喀纳斯",
            "team": "KANASI-0502",
            "start_date": "2026-05-02",
            "end_date": "2026-05-05",
            "participants": 3,
            "status": "计划中",
            "leader_name": "木拉提",
            "contact_phone": "13600003333",
            "itinerary": [
                {"date": "2026-05-02", "transport": "商务车", "route": "阿勒泰机场 -> 布尔津", "hotel": "布尔津悦景酒店"},
                {"date": "2026-05-03", "transport": "旅游巴士", "route": "布尔津 -> 喀纳斯", "hotel": "喀纳斯湖景酒店"},
                {"date": "2026-05-04", "transport": "区间车", "route": "喀纳斯 -> 禾木", "hotel": "禾木山庄"},
            ],
            "guests": [
                {"name": "马宁", "phone": "13800003331", "notes": "摄影器材较多"},
                {"name": "郭静", "phone": "13800003332", "notes": "高海拔提醒"},
                {"name": "何兵", "phone": "13800003333", "notes": "无"},
            ],
            "config": {
                "project_name": "喀纳斯湖景漫游团",
                "manual_takeover_target": "值班管家C组",
                "sms_sign_name": "TravelHub",
                "sms_provider": "aliyun",
                "weather_enabled": False,
            },
        },
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="123456")
    args = parser.parse_args()

    token = login(args.base_url, args.username, args.password)
    payloads = build_seed_payloads()

    result: list[tuple[str, str]] = []
    for item in payloads:
        trip_payload = {
            "destination": item["destination"],
            "team": item["team"],
            "start_date": item["start_date"],
            "end_date": item["end_date"],
            "participants": item["participants"],
            "status": item["status"],
            "leader_name": item["leader_name"],
            "contact_phone": item["contact_phone"],
            "itinerary": item["itinerary"],
            "guests": item["guests"],
        }
        trip_id = upsert_trip(args.base_url, token, str(item["team"]), trip_payload)
        upsert_notification_config(args.base_url, token, trip_id, dict(item["config"]))
        generate_daily_notifications(
            args.base_url,
            token,
            str(item["team"]),
            [str(day["date"]) for day in list(item["itinerary"])],
        )
        result.append((str(item["team"]), trip_id))

    print("Seed completed (idempotent upsert).")
    for team, trip_id in result:
        print(f"- {team}: trip_id={trip_id}")


if __name__ == "__main__":
    main()
