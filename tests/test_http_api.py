from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.http import app, reset_state


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def test_auth_login_and_role_resolution() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)

    admin_token = _login(client, "admin", "123456")
    user_token = _login(client, "user", "123456")

    admin_me = client.get("/api/users/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert admin_me.status_code == 200
    assert admin_me.json()["data"]["role"] == "admin"

    user_me = client.get("/api/users/me", headers={"Authorization": f"Bearer {user_token}"})
    assert user_me.status_code == 200
    assert user_me.json()["data"]["role"] == "user"
    assert user_me.json()["data"]["tenant_id"] == "tenant-a"


def test_auth_login_invalid_credentials_returns_401() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)

    response = client.post(
        "/api/auth/login", json={"username": "admin", "password": "wrong-password"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_tenant_isolation_for_trip_and_history_queries() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)
    user_token = _login(client, "user", "123456")
    partner_token = _login(client, "partner", "123456")

    user_headers = {"Authorization": f"Bearer {user_token}"}
    partner_headers = {"Authorization": f"Bearer {partner_token}"}

    created = client.post(
        "/api/trips",
        headers=user_headers,
        json={
            "destination": "赛里木湖",
            "team": "TEAM-TENANT-A",
            "start_date": "2026-07-01",
            "end_date": "2026-07-03",
            "participants": 10,
        },
    )
    assert created.status_code == 201
    trip_id = created.json()["data"]["trip"]["id"]

    forbidden_trip = client.get(f"/api/trips/{trip_id}/timeline", headers=partner_headers)
    assert forbidden_trip.status_code == 403

    partner_history = client.get("/api/notifications/history?limit=20", headers=partner_headers)
    assert partner_history.status_code == 200
    assert partner_history.json()["data"]["total"] == 0


def test_preferences_read_write() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)
    user_token = _login(client, "user", "123456")
    headers = {"Authorization": f"Bearer {user_token}"}

    initial = client.get("/api/preferences/me", headers=headers)
    assert initial.status_code == 200
    assert "channels" in initial.json()["data"]

    updated = client.put(
        "/api/preferences/me",
        headers=headers,
        json={"channels": ["email", "sms"], "quiet_hours": [22, 6], "allow_marketing": False},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["channels"] == ["email", "sms"]
    assert updated.json()["data"]["quiet_hours"] == [22, 6]
    assert updated.json()["data"]["allow_marketing"] is False


def test_template_crud_and_admin_guard() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)

    admin_token = _login(client, "admin", "123456")
    user_token = _login(client, "user", "123456")

    forbidden = client.post(
        "/api/templates",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "name": "普通用户创建",
            "content": "{{customer_name}}，你好",
            "channel": "sms",
            "notification_type": "daily_reminder",
            "is_active": True,
        },
    )
    assert forbidden.status_code == 403

    create = client.post(
        "/api/templates",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "出发前提醒",
            "content": "{{customer_name}}，您的{{destination}}行程即将开始。",
            "channel": "sms",
            "notification_type": "daily_reminder",
            "is_active": True,
        },
    )
    assert create.status_code == 201
    template_id = create.json()["data"]["id"]

    listed = client.get("/api/templates", headers={"Authorization": f"Bearer {admin_token}"})
    assert listed.status_code == 200
    assert any(item["id"] == template_id for item in listed.json()["data"]["items"])

    detail = client.get(
        f"/api/templates/{template_id}", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert detail.status_code == 200

    updated = client.put(
        f"/api/templates/{template_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_active": False, "content": "变更后的模板内容"},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["is_active"] is False

    deleted = client.delete(
        f"/api/templates/{template_id}", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert deleted.status_code == 200

    missing = client.get(
        f"/api/templates/{template_id}", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert missing.status_code == 404


def test_notification_template_alias_supports_update_and_delete() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)
    admin_token = _login(client, "admin", "123456")
    headers = {"Authorization": f"Bearer {admin_token}"}

    seeded = client.get("/api/notifications/templates", headers=headers)
    assert seeded.status_code == 200
    items = seeded.json()["data"]["items"]
    assert len(items) >= 10
    template_id = items[0]["id"]

    updated = client.put(
        f"/api/notifications/templates/{template_id}",
        headers=headers,
        json={"name": "模板别名更新测试", "is_active": False},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["name"] == "模板别名更新测试"
    assert updated.json()["data"]["is_active"] is False

    deleted = client.delete(f"/api/notifications/templates/{template_id}", headers=headers)
    assert deleted.status_code == 200


def test_agent_generates_morning_noon_evening_templates_and_admin_can_modify() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)
    admin_token = _login(client, "admin", "123456")
    user_token = _login(client, "user", "123456")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    user_headers = {"Authorization": f"Bearer {user_token}"}

    forbidden = client.post(
        "/api/notifications/templates/agent-drafts",
        headers=user_headers,
        json={
            "route": "乌鲁木齐-喀纳斯",
            "travel_stage": "行程中",
            "time_node": "每日固定时段",
            "core_work": "时段性专属温馨提示",
        },
    )
    assert forbidden.status_code == 403

    created = client.post(
        "/api/notifications/templates/agent-drafts",
        headers=admin_headers,
        json={
            "route": "乌鲁木齐-喀纳斯",
            "travel_stage": "行程中",
            "time_node": "每日固定时段",
            "core_work": "时段性专属温馨提示",
            "action_detail": "早中晚分别发送安全、天气、次日预告",
            "project_id": "proj-xinjiang",
            "template_prefix": "行中日播",
        },
    )
    assert created.status_code == 200
    payload = created.json()["data"]
    assert len(payload["drafts"]) == 3
    assert [item["time_slot"] for item in payload["drafts"]] == ["morning", "noon", "evening"]
    assert len(payload["created_template_ids"]) == 3

    template_id = payload["created_template_ids"][0]
    updated = client.put(
        f"/api/notifications/templates/{template_id}",
        headers=admin_headers,
        json={"content": "【人工修订】明日早上集合前请再次检查证件与保暖衣物。"},
    )
    assert updated.status_code == 200
    assert "人工修订" in updated.json()["data"]["content"]


def test_generate_daily_notifications_uses_multi_agent_pipeline(monkeypatch) -> None:
    async def _fake_llm(
        trip_destination: str, scene: str, prompt_override: str | None = None
    ) -> str:
        return f"【AI生成】{scene}：{trip_destination}，请关注集合时间与路线安排。"

    monkeypatch.setattr("app.services.notification_agent_service.generate_smart_message", _fake_llm)

    reset_state(purge_persistence=True)
    client = TestClient(app)
    admin_token = _login(client, "admin", "123456")
    headers = {"Authorization": f"Bearer {admin_token}"}

    created_trip = client.post(
        "/api/trips",
        headers=headers,
        json={
            "destination": "塔县-慕士塔格冰川公园-喀什",
            "team": "TEAM-AGENT-001",
            "start_date": "2026-04-20",
            "end_date": "2026-04-26",
            "participants": 18,
        },
    )
    assert created_trip.status_code == 201
    trip_id = created_trip.json()["data"]["trip"]["id"]

    patched_trip = client.put(
        f"/api/trips/{trip_id}",
        headers=headers,
        json={
            "itinerary": [
                {
                    "date": "2026-04-22",
                    "route": "塔县-慕士塔格冰川公园-喀什",
                    "hotel": "喀什万巢国际酒店",
                    "special_tags": ["冰川", "高海拔"],
                }
            ]
        },
    )
    assert patched_trip.status_code == 200

    generated = client.post(
        "/api/notifications/generate-daily",
        headers=headers,
        json={
            "group_id": "TEAM-AGENT-001",
            "date": "2026-04-22",
            "weather": "小雨 11°C",
            "core_work": "时段性专属温馨提示",
            "save_as_templates": True,
            "project_id": "proj-agent",
        },
    )
    assert generated.status_code == 200
    payload = generated.json()["data"]
    assert payload["stage"] == "行程中"
    assert payload["time_node"] == "每日固定时段"
    assert len(payload["messages"]) == 3
    assert [item["period"] for item in payload["messages"]] == ["morning", "noon", "evening"]
    assert all("AI生成" in item["message"] for item in payload["messages"])
    assert len(payload["created_template_ids"]) == 3
    assert "debug" in payload


def test_generate_daily_notifications_marks_end_date_as_checkout(monkeypatch) -> None:
    async def _fake_llm(
        trip_destination: str, scene: str, prompt_override: str | None = None
    ) -> str:
        return f"【AI生成】{scene}：{trip_destination}"

    monkeypatch.setattr("app.services.notification_agent_service.generate_smart_message", _fake_llm)

    reset_state(purge_persistence=True)
    client = TestClient(app)
    admin_token = _login(client, "admin", "123456")
    headers = {"Authorization": f"Bearer {admin_token}"}

    created_trip = client.post(
        "/api/trips",
        headers=headers,
        json={
            "destination": "乌鲁木齐",
            "team": "TEAM-END-STAGE",
            "start_date": "2026-04-20",
            "end_date": "2026-04-22",
            "participants": 12,
        },
    )
    assert created_trip.status_code == 201

    generated = client.post(
        "/api/notifications/generate-daily",
        headers=headers,
        json={
            "group_id": "TEAM-END-STAGE",
            "date": "2026-04-22",
            "weather": "晴 18°C",
            "core_work": "返程提醒",
        },
    )
    assert generated.status_code == 200
    payload = generated.json()["data"]
    assert payload["stage"] == "下团即付"
    assert payload["time_node"] == "下团即付"


def test_generate_daily_notifications_resolves_trip_by_requested_date(monkeypatch) -> None:
    async def _fake_llm(
        trip_destination: str, scene: str, prompt_override: str | None = None
    ) -> str:
        return f"【AI生成】{scene}：{trip_destination}"

    monkeypatch.setattr("app.services.notification_agent_service.generate_smart_message", _fake_llm)

    reset_state(purge_persistence=True)
    client = TestClient(app)
    admin_token = _login(client, "admin", "123456")
    headers = {"Authorization": f"Bearer {admin_token}"}

    old_trip = client.post(
        "/api/trips",
        headers=headers,
        json={
            "destination": "阿勒泰",
            "team": "TEAM-REUSED",
            "start_date": "2026-04-01",
            "end_date": "2026-04-05",
            "participants": 20,
        },
    )
    assert old_trip.status_code == 201
    old_trip_id = old_trip.json()["data"]["trip"]["id"]
    old_patch = client.put(
        f"/api/trips/{old_trip_id}",
        headers=headers,
        json={"itinerary": [{"date": "2026-04-03", "route": "旧行程路线"}]},
    )
    assert old_patch.status_code == 200

    new_trip = client.post(
        "/api/trips",
        headers=headers,
        json={
            "destination": "伊犁",
            "team": "TEAM-REUSED",
            "start_date": "2026-06-01",
            "end_date": "2026-06-05",
            "participants": 25,
        },
    )
    assert new_trip.status_code == 201
    new_trip_id = new_trip.json()["data"]["trip"]["id"]
    new_patch = client.put(
        f"/api/trips/{new_trip_id}",
        headers=headers,
        json={"itinerary": [{"date": "2026-06-03", "route": "新行程路线"}]},
    )
    assert new_patch.status_code == 200

    generated = client.post(
        "/api/notifications/generate-daily",
        headers=headers,
        json={
            "group_id": "TEAM-REUSED",
            "date": "2026-04-03",
            "weather": "晴",
            "core_work": "提醒",
        },
    )
    assert generated.status_code == 200
    payload = generated.json()["data"]
    assert payload["debug"]["route_text"] == "旧行程路线"
    assert all("旧行程路线" in item["message"] for item in payload["messages"])


def test_emergency_weather_summary_returns_ai_risk_and_trip_preview() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)
    admin_token = _login(client, "admin", "123456")
    headers = {"Authorization": f"Bearer {admin_token}"}

    response = client.get("/api/notifications/emergency-weather", headers=headers)
    assert response.status_code == 200

    data = response.json()["data"]
    assert data["title"]
    assert data["risk_level"] in {"high", "critical"}
    assert data["weather_summary"]
    assert data["ai_risk_summary"]
    assert data["affected_trip_count"] >= 1
    assert len(data["affected_trips"]) >= 1
    assert data["generated_notification"]
    assert "受影响" in data["generated_notification"] or "请" in data["generated_notification"]

    first_trip = data["affected_trips"][0]
    assert set(first_trip.keys()) >= {
        "trip_id",
        "team_id",
        "destination",
        "status",
        "traveler_count",
        "summary",
    }


def test_emergency_weather_send_supports_custom_content() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)
    admin_token = _login(client, "admin", "123456")
    headers = {"Authorization": f"Bearer {admin_token}"}

    summary = client.get("/api/notifications/emergency-weather", headers=headers)
    assert summary.status_code == 200
    data = summary.json()["data"]

    response = client.post(
        "/api/notifications/emergency-weather/send",
        headers=headers,
        json={
            "alert_id": data["alert_id"],
            "custom_content": "【紧急提醒】九寨沟沿线降雨增强，请全体游客按领队指引调整集合时间。",
            "channel": "sms",
        },
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["ok"] is True
    assert payload["sent_count"] >= 1
    assert payload["notification_id"]
    assert payload["status"] in {"sent", "manual_intervention"}


def test_project_notification_config_crud() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)
    admin_token = _login(client, "admin", "123456")
    user_token = _login(client, "user", "123456")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    user_headers = {"Authorization": f"Bearer {user_token}"}

    forbidden = client.put(
        "/api/project-configs/proj-xinjiang",
        headers=user_headers,
        json={"project_name": "新疆阿勒泰团"},
    )
    assert forbidden.status_code == 403

    updated = client.put(
        "/api/project-configs/proj-xinjiang",
        headers=admin_headers,
        json={
            "project_name": "新疆阿勒泰团",
            "weather_enabled": True,
            "qweather_location_id": "101130101",
            "qweather_lat": "43.82",
            "qweather_lon": "87.62",
            "weather_alert_thresholds": {
                "warning_levels": ["yellow", "orange", "red"],
                "min_temp_c": 2,
            },
            "sms_provider": "aliyun",
            "sms_sign_name": "新疆团",
            "sms_template_code_normal": "SMS_XJ_NORMAL",
            "sms_template_code_weather_alert": "SMS_XJ_ALERT",
            "manual_takeover_target": "管家值班群",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["project_id"] == "proj-xinjiang"
    assert updated.json()["data"]["sms_sign_name"] == "新疆团"
    assert updated.json()["data"]["weather_alert_thresholds"]["min_temp_c"] == 2

    detail = client.get("/api/project-configs/proj-xinjiang", headers=admin_headers)
    assert detail.status_code == 200
    assert detail.json()["data"]["sms_template_code_weather_alert"] == "SMS_XJ_ALERT"

    listed = client.get("/api/project-configs", headers=admin_headers)
    assert listed.status_code == 200
    assert any(item["project_id"] == "proj-xinjiang" for item in listed.json()["data"]["items"])


def test_trip_creation_triggers_notification_history_and_audit() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)
    user_token = _login(client, "user", "123456")
    headers = {"Authorization": f"Bearer {user_token}"}

    created = client.post(
        "/api/trips",
        headers=headers,
        json={
            "destination": "阿勒泰 - 禾木",
            "team": "TEAM-009",
            "start_date": "2026-05-01",
            "end_date": "2026-05-03",
            "participants": 20,
        },
    )
    assert created.status_code == 201
    trip_id = created.json()["data"]["trip"]["id"]
    assert created.json()["data"]["notification"]["ok"] is True

    history = client.get(f"/api/notifications/history?trip_id={trip_id}&limit=10", headers=headers)
    assert history.status_code == 200
    assert history.json()["data"]["total"] >= 1

    timeline = client.get(f"/api/trips/{trip_id}/timeline", headers=headers)
    assert timeline.status_code == 200
    actions = {item["action"] for item in timeline.json()["data"]["audit_logs"]}
    assert "trip_created" in actions
    assert "notification_dispatched" in actions


def test_dashboard_core_contract_returns_stats_suggestions_and_recent_items() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)
    admin_token = _login(client, "admin", "123456")
    headers = {"Authorization": f"Bearer {admin_token}"}

    created = client.post(
        "/api/trips",
        headers=headers,
        json={
            "destination": "阿勒泰禾木轻奢团",
            "team": "TEAM-DASH-001",
            "start_date": "2026-05-01",
            "end_date": "2026-05-06",
            "participants": 12,
        },
    )
    assert created.status_code == 201
    trip_id = created.json()["data"]["trip"]["id"]

    stats_response = client.get("/api/dashboard/stats", headers=headers)
    assert stats_response.status_code == 200
    stats = stats_response.json()["data"]
    assert set(stats.keys()) == {
        "today_notifications",
        "active_trips",
        "total_travelers",
        "total_users",
        "pending_notifications",
        "pending_complaints",
        "notification_success_rate",
        "avg_response_time_ms",
        "channel_growth_rate",
    }

    suggestions_response = client.get("/api/dashboard/smart-suggestions", headers=headers)
    assert suggestions_response.status_code == 200
    suggestions = suggestions_response.json()["data"]["items"]
    assert len(suggestions) >= 1
    first = suggestions[0]
    assert set(first.keys()) == {
        "id",
        "trip_id",
        "trip_name",
        "type",
        "title",
        "reason",
        "suggested_content",
        "target_count",
        "channel",
    }
    assert first["trip_id"] == trip_id

    recent_response = client.get("/api/notifications/recent?limit=5", headers=headers)
    assert recent_response.status_code == 200
    recent_items = recent_response.json()["data"]["items"]
    assert len(recent_items) >= 1
    assert set(recent_items[0].keys()) == {
        "id",
        "customer_name",
        "trip",
        "channel",
        "status",
        "created_at",
    }


def test_trip_detail_update_persists_itinerary_and_guests() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)
    user_token = _login(client, "user", "123456")
    headers = {"Authorization": f"Bearer {user_token}"}

    created = client.post(
        "/api/trips",
        headers=headers,
        json={
            "destination": "北疆深度环线",
            "team": "TEAM-DETAIL-001",
            "start_date": "2026-06-01",
            "end_date": "2026-06-05",
            "participants": 0,
        },
    )
    assert created.status_code == 201
    trip_id = created.json()["data"]["trip"]["id"]

    update_response = client.put(
        f"/api/trips/{trip_id}",
        headers=headers,
        json={
            "itinerary": [
                {
                    "date": "2026-06-01",
                    "transport": "Flight CZ1234",
                    "route": "上海 -> 乌鲁木齐",
                    "hotel": "乌鲁木齐康莱德",
                },
                {
                    "date": "2026-06-02",
                    "transport": "Private Van",
                    "route": "乌鲁木齐 -> 布尔津",
                    "hotel": "布尔津假日酒店",
                },
            ],
            "guests": [
                {"name": "张三", "phone": "13800138000", "notes": "忌辛辣"},
                {"name": "李四", "phone": "13900139000", "notes": "靠窗房"},
            ],
        },
    )
    assert update_response.status_code == 200
    updated_trip = update_response.json()["data"]
    assert len(updated_trip["itinerary"]) == 2
    assert len(updated_trip["guests"]) == 2
    assert updated_trip["participants"] == 2

    detail_response = client.get(f"/api/trips/{trip_id}", headers=headers)
    assert detail_response.status_code == 200
    detail = detail_response.json()["data"]
    assert detail["itinerary"][0]["route"] == "上海 -> 乌鲁木齐"
    assert detail["guests"][1]["name"] == "李四"
    assert detail["participants"] == 2


def test_trip_schedule_returns_route_days_and_notification_summary() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)
    user_token = _login(client, "user", "123456")
    headers = {"Authorization": f"Bearer {user_token}"}

    created = client.post(
        "/api/trips",
        headers=headers,
        json={
            "destination": "新疆环线精华团",
            "team": "TEAM-SCHEDULE-001",
            "start_date": "2026-08-01",
            "end_date": "2026-08-04",
            "participants": 0,
        },
    )
    assert created.status_code == 201
    trip_id = created.json()["data"]["trip"]["id"]

    updated = client.put(
        f"/api/trips/{trip_id}",
        headers=headers,
        json={
            "status": "进行中",
            "itinerary": [
                {
                    "date": "2026-08-01",
                    "transport": "Flight CZ6881",
                    "route": "乌鲁木齐 -> 吐鲁番",
                    "hotel": "吐鲁番万达美华",
                },
                {
                    "date": "2026-08-02",
                    "transport": "Tour Bus",
                    "route": "吐鲁番 -> 喀纳斯",
                    "hotel": "喀纳斯山庄",
                },
            ],
            "guests": [
                {"name": "王导", "phone": "13800138000", "notes": "领队"},
                {"name": "张三", "phone": "13900139000", "notes": "普通游客"},
            ],
        },
    )
    assert updated.status_code == 200

    response = client.get(f"/api/trips/{trip_id}/schedule", headers=headers)
    assert response.status_code == 200

    payload = response.json()["data"]
    assert payload["trip_id"] == trip_id
    assert payload["route_summary"] == ["乌鲁木齐", "吐鲁番", "喀纳斯"]
    assert payload["status"]["code"] == "in_progress"
    assert payload["traveler_count"] == 2
    assert payload["leader"]["name"] == "王导"
    assert payload["leader"]["phone"] == "13800138000"
    assert payload["days"][0]["title"] == "Day 1"
    assert payload["days"][0]["segments"][0]["transport"] == "Flight CZ6881"
    assert payload["days"][1]["segments"][0]["hotel"] == "喀纳斯山庄"
    assert payload["notification_summary"]["recent_count"] >= 1


def test_notifications_send_supports_custom_content_and_template_send() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)
    admin_token = _login(client, "admin", "123456")
    headers = {"Authorization": f"Bearer {admin_token}"}

    template_response = client.post(
        "/api/notifications/templates",
        headers=headers,
        json={
            "name": "发送测试模板",
            "content": "尊敬的{{customer_name}}，欢迎参加{{destination}}行程",
            "channel": "sms",
            "notification_type": "daily_reminder",
            "is_active": True,
        },
    )
    assert template_response.status_code == 201
    template_id = template_response.json()["data"]["id"]

    custom_send = client.post(
        "/api/notifications/send",
        headers=headers,
        json={
            "custom_content": "这是一条人工编辑短信",
            "channel": "sms",
            "customer_name": "王五",
            "customer_phone": "13700137000",
            "trip": "MANUAL-TRIP-001",
        },
    )
    assert custom_send.status_code == 200
    custom_payload = custom_send.json()["data"]
    assert custom_payload["ok"] is True
    assert custom_payload["notification_id"]

    template_send = client.post(
        "/api/notifications/send",
        headers=headers,
        json={
            "template_id": template_id,
            "channel": "sms",
            "customer_name": "赵六",
            "customer_phone": "13600136000",
            "destination": "伊犁草原",
            "trip": "MANUAL-TRIP-002",
        },
    )
    assert template_send.status_code == 200
    template_payload = template_send.json()["data"]
    assert template_payload["ok"] is True
    assert template_payload["notification_id"]

    recent_response = client.get("/api/notifications/recent?limit=10", headers=headers)
    assert recent_response.status_code == 200
    recent_items = recent_response.json()["data"]["items"]
    assert len(recent_items) >= 2
    assert any(item["trip"] == "MANUAL-TRIP-001" for item in recent_items)
    assert any(item["trip"] == "MANUAL-TRIP-002" for item in recent_items)


def test_analytics_metrics_returns_itinerary_rows_from_backend() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)
    admin_token = _login(client, "admin", "123456")
    headers = {"Authorization": f"Bearer {admin_token}"}

    created = client.post(
        "/api/trips",
        headers=headers,
        json={
            "destination": "喀纳斯湖景团",
            "team": "TEAM-ANA-001",
            "start_date": "2026-07-10",
            "end_date": "2026-07-13",
            "participants": 2,
        },
    )
    assert created.status_code == 201
    trip_id = created.json()["data"]["trip"]["id"]

    updated = client.put(
        f"/api/trips/{trip_id}",
        headers=headers,
        json={
            "status": "进行中",
            "itinerary": [
                {
                    "date": "2026-07-10",
                    "transport": "SUV",
                    "route": "乌鲁木齐 -> 布尔津",
                    "hotel": "布尔津美居",
                }
            ],
            "guests": [
                {"name": "A", "phone": "13500135000", "notes": ""},
                {"name": "B", "phone": "13400134000", "notes": ""},
            ],
        },
    )
    assert updated.status_code == 200

    metrics_response = client.get("/api/analytics/metrics", headers=headers)
    assert metrics_response.status_code == 200
    payload = metrics_response.json()["data"]
    assert "summary" in payload
    assert "metrics" in payload
    assert "charts" in payload
    assert "notification_trend" in payload["charts"]
    assert "channel_distribution" in payload["charts"]
    assert "itinerary_rows" in payload
    assert len(payload["itinerary_rows"]) >= 1
    assert payload["itinerary_rows"][0]["route"] == "乌鲁木齐 -> 布尔津"


def test_health_check_detail() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["data"]["status"] == "ok"

    detail = client.get("/api/health/detail")
    assert detail.status_code == 200
    assert detail.json()["data"]["status"] == "ok"
    assert "components" in detail.json()["data"]


def test_analytics_metrics_returns_seeded_structured_data() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)
    admin_token = _login(client, "admin", "123456")
    headers = {"Authorization": f"Bearer {admin_token}"}

    metrics_response = client.get("/api/analytics/metrics", headers=headers)
    assert metrics_response.status_code == 200

    payload = metrics_response.json()["data"]
    assert payload["metrics"]["notification_success_rate"].endswith("%")
    assert payload["metrics"]["notification_retry_rate"].endswith("%")
    assert payload["metrics"]["notification_manual_takeover_rate"].endswith("%")
    assert "rule_publish_lead_time" in payload["metrics"]
    assert "cross_tenant_forbidden_count" in payload["metrics"]
    assert payload["metrics"]["avg_response_time"].endswith("ms")
    assert payload["metrics"]["user_satisfaction"].endswith("/5")
    assert len(payload["channel_performance"]) >= 1
    assert len(payload["top_trips"]) >= 1


def test_update_trip_rejects_blank_team_fields_and_keeps_original_value() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)
    user_token = _login(client, "user", "123456")
    headers = {"Authorization": f"Bearer {user_token}"}

    created = client.post(
        "/api/trips",
        headers=headers,
        json={
            "destination": "喀纳斯",
            "team": "TEAM-ORIGINAL",
            "start_date": "2026-06-01",
            "end_date": "2026-06-05",
            "participants": 12,
        },
    )
    assert created.status_code == 201
    trip_id = created.json()["data"]["trip"]["id"]

    blank_team = client.put(
        f"/api/trips/{trip_id}",
        headers=headers,
        json={"team": "   "},
    )
    assert blank_team.status_code == 400

    blank_team_id = client.put(
        f"/api/trips/{trip_id}",
        headers=headers,
        json={"team_id": "   "},
    )
    assert blank_team_id.status_code == 400

    detail = client.get(f"/api/trips/{trip_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["data"]["team_id"] == "TEAM-ORIGINAL"
    assert detail.json()["data"]["team"] == "TEAM-ORIGINAL"


def test_notification_rules_contract_smoke() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)
    admin_token = _login(client, "admin", "123456")
    headers = {"Authorization": f"Bearer {admin_token}"}

    listed_before = client.get("/api/notifications/rules", headers=headers)
    assert listed_before.status_code == 200
    assert listed_before.json()["code"] == 200
    assert "message" in listed_before.json()

    created = client.post(
        "/api/notifications/rules",
        headers=headers,
        json={
            "name": "规则契约冒烟",
            "stage": "before_departure",
            "time_slot": "AM",
            "scene": "天气",
            "channels": ["短信", "企业微信"],
            "priority": 10,
            "enabled": True,
            "conditions": {"rain": True},
        },
    )
    assert created.status_code == 201
    created_data = created.json()["data"]
    rule_id = created_data["id"]
    assert created_data["stage"] == "pre_trip"
    assert created_data["time_slot"] == "morning"
    assert created_data["scene"] == "weather_alert"
    assert created_data["channels"] == ["sms", "wechat_work_group"]

    fetched = client.get(f"/api/notifications/rules/{rule_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["data"]["id"] == rule_id

    updated = client.put(
        f"/api/notifications/rules/{rule_id}",
        headers=headers,
        json={"enabled": False, "time_slot": "night", "priority": 5},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["enabled"] is False
    assert updated.json()["data"]["time_slot"] == "night"
    assert updated.json()["data"]["priority"] == 5

    invalid = client.post(
        "/api/notifications/rules",
        headers=headers,
        json={"name": "非法规则", "stage": "bad-stage", "time_slot": "morning", "scene": "normal"},
    )
    assert invalid.status_code == 400
    assert invalid.json()["code"] == 400

    deleted = client.delete(f"/api/notifications/rules/{rule_id}", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["data"]["deleted"] is True

    listed_after = client.get("/api/notifications/rules", headers=headers)
    assert listed_after.status_code == 200
    assert all(item["id"] != rule_id for item in listed_after.json()["data"]["items"])


def test_notification_rule_approval_workflow_and_simulation() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)
    admin_token = _login(client, "admin", "123456")
    headers = {"Authorization": f"Bearer {admin_token}"}

    created = client.post(
        "/api/notifications/rules",
        headers=headers,
        json={
            "name": "审批流规则",
            "stage": "pre_trip",
            "time_slot": "morning",
            "scene": "normal",
            "channels": ["sms"],
            "priority": 1,
            "enabled": False,
            "conditions": {"vip": True},
        },
    )
    assert created.status_code == 201
    rule_id = created.json()["data"]["id"]
    assert created.json()["data"]["status"] == "draft"

    before_publish = client.post(
        "/api/notifications/rules/simulate",
        headers=headers,
        json={
            "stage": "pre_trip",
            "time_slot": "morning",
            "scene": "normal",
            "context": {"vip": True},
        },
    )
    assert before_publish.status_code == 200
    assert before_publish.json()["data"]["matches"] == []

    submitted = client.post(f"/api/notifications/rules/{rule_id}/submit", headers=headers)
    assert submitted.status_code == 200
    assert submitted.json()["data"]["status"] == "pending_approval"

    approved = client.post(
        f"/api/notifications/rules/{rule_id}/approve",
        headers=headers,
        json={"comment": "looks good"},
    )
    assert approved.status_code == 200
    assert approved.json()["data"]["status"] == "approved"

    published = client.post(
        f"/api/notifications/rules/{rule_id}/publish",
        headers=headers,
        json={"comment": "publish now"},
    )
    assert published.status_code == 200
    assert published.json()["data"]["status"] == "published"

    simulated = client.post(
        "/api/notifications/rules/simulate",
        headers=headers,
        json={
            "stage": "pre_trip",
            "time_slot": "morning",
            "scene": "normal",
            "context": {"vip": True},
        },
    )
    assert simulated.status_code == 200
    assert len(simulated.json()["data"]["matches"]) >= 1
    assert simulated.json()["data"]["matches"][0]["id"] == rule_id


def test_default_seed_data_visible_for_admin() -> None:
    reset_state(purge_persistence=True)
    client = TestClient(app)
    admin_token = _login(client, "admin", "123456")
    headers = {"Authorization": f"Bearer {admin_token}"}

    trips = client.get("/api/trips", headers=headers)
    assert trips.status_code == 200
    assert trips.json()["data"]["total"] >= 1

    rules = client.get("/api/notifications/rules", headers=headers)
    assert rules.status_code == 200
    assert rules.json()["data"]["total"] >= 1


def test_delete_template_rebinds_rule_dependency_in_mysql(monkeypatch) -> None:
    monkeypatch.setenv("TRAVEL_NOTIFICATION_MYSQL_HOST", "127.0.0.1")
    monkeypatch.setenv("TRAVEL_NOTIFICATION_MYSQL_PORT", "3306")
    monkeypatch.setenv("TRAVEL_NOTIFICATION_MYSQL_USER", "root")
    monkeypatch.setenv("TRAVEL_NOTIFICATION_MYSQL_PASSWORD", "123456")
    monkeypatch.setenv("TRAVEL_NOTIFICATION_MYSQL_DATABASE", "travel_notification_system")
    reset_state(purge_persistence=True)
    client = TestClient(app)
    admin_token = _login(client, "admin", "123456")
    headers = {"Authorization": f"Bearer {admin_token}"}

    template_a = client.post(
        "/api/templates",
        headers=headers,
        json={
            "name": "待删除模板A",
            "content": "A: {{customer_name}}",
            "channel": "sms",
            "notification_type": "daily_reminder",
            "is_active": True,
        },
    )
    assert template_a.status_code == 201
    template_a_id = template_a.json()["data"]["id"]

    template_b = client.post(
        "/api/templates",
        headers=headers,
        json={
            "name": "保留模板B",
            "content": "B: {{customer_name}}",
            "channel": "sms",
            "notification_type": "daily_reminder",
            "is_active": True,
        },
    )
    assert template_b.status_code == 201

    created_rule = client.post(
        "/api/notifications/rules",
        headers=headers,
        json={
            "name": "模板依赖规则",
            "stage": "pre_trip",
            "time_slot": "morning",
            "scene": "normal",
            "channels": ["sms"],
            "template_id": template_a_id,
            "enabled": True,
            "priority": 30,
        },
    )
    assert created_rule.status_code == 201
    rule_id = created_rule.json()["data"]["id"]
    assert created_rule.json()["data"]["template_id"] == template_a_id

    deleted = client.delete(f"/api/templates/{template_a_id}", headers=headers)
    assert deleted.status_code == 200

    listed = client.get("/api/templates", headers=headers)
    assert listed.status_code == 200
    ids = [item["id"] for item in listed.json()["data"]["items"]]
    assert template_a_id not in ids

    rule_detail = client.get(f"/api/notifications/rules/{rule_id}", headers=headers)
    assert rule_detail.status_code == 200
