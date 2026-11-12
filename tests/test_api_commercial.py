from __future__ import annotations

from fastapi.testclient import TestClient


def _create_app(monkeypatch, tmp_path):
    monkeypatch.setenv("TRAVEL_NOTIFICATION_DB_DIR", str(tmp_path))
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("NOTIFICATION_QUEUE_INTERVAL_SECONDS", "3600")
    from app.api.http import create_app

    return create_app()


def _login(client: TestClient, username: str = "admin", password: str = "123456") -> str:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register_tenant(client: TestClient, phone: str, username: str) -> dict:
    code_response = client.post(
        "/api/auth/sms-code",
        json={"phone": phone, "purpose": "register"},
    )
    assert code_response.status_code == 200, code_response.text
    code = code_response.json()["data"]["debug_code"]
    response = client.post(
        "/api/auth/register",
        json={
            "tenant_name": "商业化测试旅行社",
            "username": username,
            "password": "secret123",
            "phone": phone,
            "code": code,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def test_public_plans_endpoint(monkeypatch, tmp_path) -> None:
    app = _create_app(monkeypatch, tmp_path)
    with TestClient(app) as client:
        response = client.get("/api/public/plans")
        assert response.status_code == 200
        data = response.json()["data"]
        assert {plan["code"] for plan in data["plans"]} >= {"free", "starter"}
        assert data["payment_methods"]


def test_sms_registration_and_login_flow(monkeypatch, tmp_path) -> None:
    app = _create_app(monkeypatch, tmp_path)
    with TestClient(app) as client:
        registered = _register_tenant(client, "13900000001", "newowner")
        assert registered["user"]["role"] == "admin"
        token = registered["tokens"]["access_token"]
        me = client.get("/api/users/me", headers=_auth(token))
        assert me.status_code == 200
        assert me.json()["data"]["tenant_id"].startswith("tenant-")

        sms_code = client.post(
            "/api/auth/sms-code",
            json={"phone": "13900000001", "purpose": "login"},
        ).json()["data"]["debug_code"]
        login = client.post(
            "/api/auth/login-sms",
            json={"phone": "13900000001", "code": sms_code},
        )
        assert login.status_code == 200
        assert login.json()["data"]["tokens"]["access_token"]


def test_billing_mock_order_activates_paid_plan(monkeypatch, tmp_path) -> None:
    app = _create_app(monkeypatch, tmp_path)
    with TestClient(app) as client:
        token = _login(client)
        subscription = client.get("/api/billing/subscription", headers=_auth(token))
        assert subscription.status_code == 200
        assert subscription.json()["data"]["subscription"]["status"] == "trialing"

        created = client.post(
            "/api/billing/orders",
            headers=_auth(token),
            json={"plan_code": "starter", "provider": "mock"},
        )
        assert created.status_code == 201, created.text
        order = created.json()["data"]
        assert order["status"] == "pending"

        paid = client.post(
            f"/api/billing/orders/{order['order_no']}/mock-pay",
            headers=_auth(token),
        )
        assert paid.status_code == 200, paid.text
        assert paid.json()["data"]["order"]["status"] == "paid"

        refreshed = client.get("/api/billing/subscription", headers=_auth(token)).json()["data"]
        assert refreshed["plan"]["code"] == "starter"
        assert refreshed["subscription"]["status"] == "active"
        assert refreshed["usage"]["sms_quota"] == 2000


def test_tenant_profile_and_user_management(monkeypatch, tmp_path) -> None:
    app = _create_app(monkeypatch, tmp_path)
    with TestClient(app) as client:
        token = _login(client)
        updated = client.put(
            "/api/admin/tenant-profile",
            headers=_auth(token),
            json={"name": "沙笛旅行·商业化版", "contact_phone": "13900000002"},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["data"]["name"] == "沙笛旅行·商业化版"

        created = client.post(
            "/api/admin/users",
            headers=_auth(token),
            json={
                "username": "operator1",
                "password": "secret123",
                "role": "user",
                "phone": "13900000003",
            },
        )
        assert created.status_code == 201, created.text
        assert created.json()["data"]["username"] == "operator1"

        listed = client.get("/api/admin/users", headers=_auth(token))
        assert listed.status_code == 200
        usernames = {item["username"] for item in listed.json()["data"]["items"]}
        assert "operator1" in usernames


def test_payment_notify_rejects_invalid_signature(monkeypatch, tmp_path) -> None:
    app = _create_app(monkeypatch, tmp_path)
    with TestClient(app) as client:
        response = client.post(
            "/api/payments/epay/notify",
            data={"out_trade_no": "TN1", "money": "299.00", "sign": "bad"},
        )
        assert response.status_code == 400
        assert response.text.startswith("fail")


def test_login_rate_limit_returns_429(monkeypatch, tmp_path) -> None:
    app = _create_app(monkeypatch, tmp_path)
    with TestClient(app) as client:
        for _ in range(5):
            response = client.post(
                "/api/auth/login",
                json={"username": "admin", "password": "wrong"},
            )
            assert response.status_code == 401
        blocked = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "wrong"},
        )
        assert blocked.status_code == 429
        assert blocked.json()["error_code"] == "login_rate_limited"


def test_operator_endpoints_require_platform_operator(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("BOOTSTRAP_OPERATOR_USERNAME", "platformops")
    monkeypatch.setenv("BOOTSTRAP_OPERATOR_PASSWORD", "secret123")
    app = _create_app(monkeypatch, tmp_path)
    with TestClient(app) as client:
        admin_token = _login(client)
        forbidden = client.get("/api/operator/billing/overview", headers=_auth(admin_token))
        assert forbidden.status_code == 403

        operator_token = _login(client, "platformops", "secret123")
        overview = client.get("/api/operator/billing/overview", headers=_auth(operator_token))
        assert overview.status_code == 200
        assert "revenue_cents" in overview.json()["data"]
        tenants = client.get("/api/operator/tenants", headers=_auth(operator_token))
        assert tenants.status_code == 200
        assert tenants.json()["data"]["total"] >= 1


def test_tenant_admin_cannot_create_platform_operator(monkeypatch, tmp_path) -> None:
    app = _create_app(monkeypatch, tmp_path)
    with TestClient(app) as client:
        token = _login(client)
        response = client.post(
            "/api/admin/users",
            headers=_auth(token),
            json={"username": "sneakyops", "password": "secret123", "role": "operator"},
        )
        assert response.status_code == 400


def test_last_admin_cannot_be_disabled_or_demoted(monkeypatch, tmp_path) -> None:
    app = _create_app(monkeypatch, tmp_path)
    with TestClient(app) as client:
        token = _login(client)
        demote = client.put(
            "/api/admin/users/admin",
            headers=_auth(token),
            json={"role": "user"},
        )
        assert demote.status_code == 400
        assert demote.json()["error_code"] == "last_admin"
        disable = client.put(
            "/api/admin/users/admin",
            headers=_auth(token),
            json={"status": "disabled"},
        )
        assert disable.status_code == 400


def test_security_headers_are_present(monkeypatch, tmp_path) -> None:
    app = _create_app(monkeypatch, tmp_path)
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "Content-Security-Policy" in response.headers
        assert response.headers["Cache-Control"] == "no-store"


def test_refresh_token_rotation_and_logout_revocation(monkeypatch, tmp_path) -> None:
    app = _create_app(monkeypatch, tmp_path)
    with TestClient(app) as client:
        login = client.post(
            "/api/auth/login", json={"username": "admin", "password": "123456"}
        ).json()["data"]
        first_refresh = login["refresh_token"]
        rotated = client.post(
            "/api/auth/refresh", json={"refresh_token": first_refresh}
        )
        assert rotated.status_code == 200
        second_refresh = rotated.json()["data"]["refresh_token"]
        assert second_refresh != first_refresh

        replay = client.post("/api/auth/refresh", json={"refresh_token": first_refresh})
        assert replay.status_code == 401

        access_token = rotated.json()["data"]["access_token"]
        client.post("/api/auth/logout", headers=_auth(access_token))
        after_logout = client.post(
            "/api/auth/refresh", json={"refresh_token": second_refresh}
        )
        assert after_logout.status_code == 401


def test_request_body_limit_returns_413(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("MAX_REQUEST_BODY_BYTES", "128")
    app = _create_app(monkeypatch, tmp_path)
    with TestClient(app) as client:
        response = client.post(
            "/api/auth/login",
            content=b'{"username":"admin","password":"' + b"x" * 512 + b'"}',
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 413


def test_disabled_user_token_is_rejected(monkeypatch, tmp_path) -> None:
    app = _create_app(monkeypatch, tmp_path)
    with TestClient(app) as client:
        admin_token = _login(client)
        user_token = _login(client, "user")
        assert client.get("/api/users/me", headers=_auth(user_token)).status_code == 200

        disabled = client.put(
            "/api/admin/users/user",
            headers=_auth(admin_token),
            json={"status": "disabled"},
        )
        assert disabled.status_code == 200
        assert client.get("/api/users/me", headers=_auth(user_token)).status_code == 401


def test_operator_can_refund_paid_order(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("BOOTSTRAP_OPERATOR_USERNAME", "platformops")
    monkeypatch.setenv("BOOTSTRAP_OPERATOR_PASSWORD", "secret123")
    app = _create_app(monkeypatch, tmp_path)
    with TestClient(app) as client:
        admin_token = _login(client)
        order = client.post(
            "/api/billing/orders",
            headers=_auth(admin_token),
            json={"plan_code": "starter", "provider": "mock"},
        ).json()["data"]
        client.post(
            f"/api/billing/orders/{order['order_no']}/mock-pay",
            headers=_auth(admin_token),
        )
        operator_token = _login(client, "platformops", "secret123")
        refunded = client.post(
            f"/api/operator/orders/{order['order_no']}/refund",
            headers=_auth(operator_token),
            json={"downgrade": True},
        )
        assert refunded.status_code == 200
        assert refunded.json()["data"]["status"] == "refunded"
        subscription = client.get(
            "/api/billing/subscription", headers=_auth(admin_token)
        ).json()["data"]
        assert subscription["plan"]["code"] == "free"


def test_regular_user_cannot_write_notification_rules(monkeypatch, tmp_path) -> None:
    app = _create_app(monkeypatch, tmp_path)
    with TestClient(app) as client:
        user_token = _login(client, "user")
        listed = client.get("/api/notifications/rules", headers=_auth(user_token))
        assert listed.status_code == 200
        denied = client.post(
            "/api/notifications/rules",
            headers=_auth(user_token),
            json={
                "name": "member-rule",
                "stage": "pre_trip",
                "time_slot": "morning",
                "scene": "normal",
                "channels": ["sms"],
            },
        )
        assert denied.status_code == 403

        admin_token = _login(client)
        created = client.post(
            "/api/notifications/rules",
            headers=_auth(admin_token),
            json={
                "name": "admin-rule",
                "stage": "pre_trip",
                "time_slot": "morning",
                "scene": "normal",
                "channels": ["sms"],
            },
        )
        assert created.status_code == 201


def test_metrics_token_protection(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("METRICS_TOKEN", "metrics-secret")
    app = _create_app(monkeypatch, tmp_path)
    with TestClient(app) as client:
        denied = client.get("/api/health/metrics")
        assert denied.status_code == 403
        allowed = client.get(
            "/api/health/metrics", headers={"X-Metrics-Token": "metrics-secret"}
        )
        assert allowed.status_code == 200
        assert "counters" in allowed.json()["data"]


def test_api_docs_disabled_in_production(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TRAVEL_NOTIFICATION_DB_DIR", str(tmp_path))
    monkeypatch.setenv("NOTIFICATION_QUEUE_INTERVAL_SECONDS", "3600")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "production-pass")
    from app.api.http import create_app

    app = create_app()
    with TestClient(app) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404


def test_operator_tenant_list_excludes_platform_tenant(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("BOOTSTRAP_OPERATOR_USERNAME", "platformops")
    monkeypatch.setenv("BOOTSTRAP_OPERATOR_PASSWORD", "secret123")
    app = _create_app(monkeypatch, tmp_path)
    with TestClient(app) as client:
        token = _login(client, "platformops", "secret123")
        tenants = client.get("/api/operator/tenants", headers=_auth(token)).json()["data"]["items"]
        assert all(item["tenant_id"] != "platform" for item in tenants)
        overview = client.get(
            "/api/operator/billing/overview", headers=_auth(token)
        ).json()["data"]
        assert all(order["tenant_id"] != "platform" for order in overview["orders"])


def test_pending_orders_are_capped(monkeypatch, tmp_path) -> None:
    app = _create_app(monkeypatch, tmp_path)
    with TestClient(app) as client:
        token = _login(client)
        for _ in range(7):
            created = client.post(
                "/api/billing/orders",
                headers=_auth(token),
                json={"plan_code": "starter", "provider": "mock"},
            )
            assert created.status_code == 201
        orders = client.get("/api/billing/orders", headers=_auth(token)).json()["data"]["items"]
        pending = [order for order in orders if order["status"] == "pending"]
        assert len(pending) <= 4
