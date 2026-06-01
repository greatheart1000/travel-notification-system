from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.sms_scheduler_demo import (
    SmsConfig,
    SmsSendLogStore,
    SmsService,
    build_demo_data,
    create_api_app,
    load_sms_config,
    process_rule,
    render_template,
)


class CollectingSmsService(SmsService):
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def send_sms(self, phone: str, template_id: str, params: dict[str, Any]) -> None:
        self.calls.append((phone, template_id, params))


class FailingOnceSmsService(SmsService):
    def __init__(self) -> None:
        self.calls = 0

    def send_sms(self, phone: str, template_id: str, params: dict[str, Any]) -> None:
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("provider unavailable")


def make_log_store(tmp_path: Path) -> SmsSendLogStore:
    return SmsSendLogStore(tmp_path / "sms_send_log.sqlite3")


def test_render_template_replaces_supported_variables() -> None:
    assert (
        render_template(
            "导游：{{leader_name}} 天气：{{weather}} 行程：{{today_activity}} 温度：{{temperature}}",
            {
                "leader_name": "张导",
                "weather": "晴",
                "today_activity": "集合出发",
                "temperature": "18°C",
            },
        )
        == "导游：张导 天气：晴 行程：集合出发 温度：18°C"
    )


def test_process_rule_sends_per_user_and_matches_campaigns_by_trip_tag(tmp_path: Path) -> None:
    data = build_demo_data(date(2026, 5, 2))
    sms_service = CollectingSmsService()
    log_store = make_log_store(tmp_path)

    try:
        for rule in data.sms_rules:
            process_rule(
                data,
                rule,
                sms_service,
                log_store,
                current_at=datetime(2026, 5, 2, 9, 0),
                force=True,
            )
    finally:
        log_store.close()

    per_rule = Counter(params["rule_id"] for _, _, params in sms_service.calls)
    per_trip = Counter(params["trip_id"] for _, _, params in sms_service.calls)
    per_campaign = Counter(params["campaign_id"] for _, _, params in sms_service.calls)

    assert len(sms_service.calls) == 34
    assert per_rule == {
        "departure_minus_3": 6,
        "departure_minus_1": 6,
        "daily_0700": 6,
        "daily_1200": 6,
        "daily_2000": 6,
        "special_horse_riding": 2,
        "special_high_altitude": 2,
    }
    assert per_trip == {
        "trip-japan-sakura": 10,
        "trip-africa-adventure": 12,
        "trip-europe-luxury": 12,
    }
    assert per_campaign["japan_pre_3"] == 2
    assert per_campaign["africa_pre_3"] == 2
    assert per_campaign["europe_pre_3"] == 2
    assert per_campaign["special_horse_riding_safety"] == 2
    assert per_campaign["special_high_altitude_safety"] == 2
    assert all(phone.startswith("138") for phone, _, _ in sms_service.calls)


def test_idempotency_skips_same_user_rule_date_on_repeated_runs(tmp_path: Path) -> None:
    data = build_demo_data(date(2026, 5, 2))
    rule = next(rule for rule in data.sms_rules if rule.id == "departure_minus_3")
    sms_service = CollectingSmsService()
    log_store = make_log_store(tmp_path)

    try:
        first_count = process_rule(
            data,
            rule,
            sms_service,
            log_store,
            current_at=datetime(2026, 5, 2, 9, 0),
            force=True,
        )
        second_count = process_rule(
            data,
            rule,
            sms_service,
            log_store,
            current_at=datetime(2026, 5, 2, 10, 0),
            force=True,
        )
        assert first_count == 6
        assert second_count == 0
        assert len(sms_service.calls) == 6
        assert log_store.count_logs("success") == 6
        assert log_store.count_logs("failed") == 0
    finally:
        log_store.close()


def test_failed_send_is_logged_and_can_retry_later(tmp_path: Path) -> None:
    data = build_demo_data(date(2026, 5, 2))
    rule = next(rule for rule in data.sms_rules if rule.id == "special_horse_riding")
    sms_service = FailingOnceSmsService()
    log_store = make_log_store(tmp_path)

    try:
        first_count = process_rule(
            data,
            rule,
            sms_service,
            log_store,
            current_at=datetime(2026, 5, 2, 9, 0),
            force=True,
        )
        second_count = process_rule(
            data,
            rule,
            sms_service,
            log_store,
            current_at=datetime(2026, 5, 2, 10, 0),
            force=True,
        )
        assert first_count == 1
        assert second_count == 1
        assert sms_service.calls == 3
        assert log_store.count_logs("failed") == 1
        assert log_store.count_logs("success") == 2
    finally:
        log_store.close()


def test_load_sms_config_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("SMS_MODE", "mock")
    monkeypatch.setenv("SMS_AK", "ak-test")
    monkeypatch.setenv("SMS_SK", "sk-test")
    monkeypatch.setenv("SMS_TEMPLATE_ID", "tpl-test")
    monkeypatch.setenv("SMS_SIGNATURE_ID", "sig-test")

    config = load_sms_config()

    assert config.sms_mode == "mock"
    assert config.ak == "ak-test"
    assert config.sk == "sk-test"
    assert config.template_id == "tpl-test"
    assert config.signature_id == "sig-test"


def test_baidu_mode_is_prepared_but_not_implemented() -> None:
    sms_service = SmsService(SmsConfig(sms_mode="baidu", ak="ak", sk="sk"))

    try:
        sms_service.send_sms("13800000000", "tpl", {"signature_id": "sig"})
    except NotImplementedError as exc:
        assert "Baidu SMS API call is not implemented yet" in str(exc)
    else:
        raise AssertionError("baidu mode should be an explicit TODO placeholder")


def test_api_can_trigger_sms_and_query_logs(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    data = build_demo_data(date(2026, 5, 2))
    sms_service = CollectingSmsService()
    log_store = make_log_store(tmp_path)
    app = create_api_app(data=data, sms_service=sms_service, log_store=log_store)

    try:
        client = TestClient(app)
        first = client.post("/trigger-sms", json={"rule_id": "departure_minus_3", "force": True})
        second = client.post("/trigger-sms", json={"rule_id": "departure_minus_3", "force": True})
        logs = client.get("/sms-logs", params={"status": "success", "limit": 10})

        assert first.status_code == 200
        assert first.json()["sent"] == 6
        assert second.status_code == 200
        assert second.json()["sent"] == 0
        assert logs.status_code == 200
        assert len(logs.json()["logs"]) == 6
        assert len(sms_service.calls) == 6
    finally:
        log_store.close()
