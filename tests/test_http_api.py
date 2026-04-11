from __future__ import annotations

import json

from app.api.http import dispatch_request


def test_auth_login_and_me_endpoint() -> None:
    login_res = dispatch_request(
        "POST",
        "/api/auth/login",
        body=json.dumps({"username": "admin", "password": "123456"}),
    )
    assert login_res.status == 200
    token = login_res.body["data"]["access_token"]

    me_res = dispatch_request("GET", "/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status == 200
    assert me_res.body["data"]["username"] == "admin"


def test_trip_crud_endpoints() -> None:
    create_res = dispatch_request(
        "POST",
        "/api/trips",
        body=json.dumps(
            {
                "destination": "阿勒泰 - 禾木",
                "team": "TEAM-009",
                "start_date": "2026-05-01",
                "end_date": "2026-05-03",
                "participants": 20,
            }
        ),
    )
    assert create_res.status == 200
    trip_id = create_res.body["data"]["id"]

    list_res = dispatch_request("GET", "/api/trips")
    assert list_res.status == 200
    assert any(item["id"] == trip_id for item in list_res.body["data"]["items"])

    update_res = dispatch_request("PUT", f"/api/trips/{trip_id}", body=json.dumps({"status": "已完成"}))
    assert update_res.status == 200
    assert update_res.body["data"]["status"] == "已完成"

    delete_res = dispatch_request("DELETE", f"/api/trips/{trip_id}")
    assert delete_res.status == 200


def test_dashboard_notifications_and_analytics_endpoints() -> None:
    stats_res = dispatch_request("GET", "/api/dashboard/stats")
    assert stats_res.status == 200
    assert "today_notifications" in stats_res.body["data"]

    tpl_res = dispatch_request("GET", "/api/notifications/templates")
    assert tpl_res.status == 200
    assert tpl_res.body["data"]["total"] >= 1

    send_res = dispatch_request(
        "POST",
        "/api/notifications/send",
        body=json.dumps({"template_id": "tpl-001", "customer_name": "测试用户", "trip": "测试行程"}),
    )
    assert send_res.status == 200
    assert send_res.body["data"]["ok"] is True

    recent_res = dispatch_request("GET", "/api/notifications/recent?limit=2")
    assert recent_res.status == 200
    assert recent_res.body["data"]["total"] <= 2

    analytics_res = dispatch_request("GET", "/api/analytics/metrics")
    assert analytics_res.status == 200
    assert "metrics" in analytics_res.body["data"]
