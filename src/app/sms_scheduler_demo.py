"""Commercial-ready mock SMS scheduler prepared for Baidu SMS integration.

Run once for a deterministic demo:
    PYTHONPATH=src python -m app.sms_scheduler_demo --run-once

Run as a live APScheduler process:
    PYTHONPATH=src python -m app.sms_scheduler_demo --demo-seconds 3
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import date, datetime, time as clock_time, timedelta
from pathlib import Path
from threading import Lock
from typing import Any, Literal

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Query
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

TEMPLATE_PATTERN = re.compile(r"{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*}}")
DEFAULT_SIGNATURE_ID = "mock-signature-id"
DEFAULT_TEMPLATE_ID = "mock-template-id"
DEFAULT_SMS_LOG_DB_PATH = Path("sms_send_log.sqlite3")
SmsMode = Literal["mock", "baidu"]
SmsSendStatus = Literal["success", "failed", "skipped"]


@dataclass(frozen=True)
class SmsConfig:
    ak: str = ""
    sk: str = ""
    template_id: str = DEFAULT_TEMPLATE_ID
    signature_id: str = DEFAULT_SIGNATURE_ID
    sms_mode: SmsMode = "mock"


def load_sms_config(config_path: str | Path | None = None) -> SmsConfig:
    raw: dict[str, Any] = {}
    if config_path:
        path = Path(config_path)
        if path.exists():
            raw.update(json.loads(path.read_text(encoding="utf-8")))

    raw.update(
        {
            "ak": os.getenv("BAIDU_SMS_AK") or os.getenv("SMS_AK") or raw.get("ak", ""),
            "sk": os.getenv("BAIDU_SMS_SK") or os.getenv("SMS_SK") or raw.get("sk", ""),
            "template_id": os.getenv("BAIDU_SMS_TEMPLATE_ID")
            or os.getenv("SMS_TEMPLATE_ID")
            or raw.get("template_id", DEFAULT_TEMPLATE_ID),
            "signature_id": os.getenv("BAIDU_SMS_SIGNATURE_ID")
            or os.getenv("SMS_SIGNATURE_ID")
            or raw.get("signature_id", DEFAULT_SIGNATURE_ID),
            "sms_mode": os.getenv("SMS_MODE") or raw.get("sms_mode", "mock"),
        }
    )

    sms_mode = str(raw.get("sms_mode", "mock")).lower()
    if sms_mode not in {"mock", "baidu"}:
        raise ValueError("sms_mode must be 'mock' or 'baidu'")

    return SmsConfig(
        ak=str(raw.get("ak", "")),
        sk=str(raw.get("sk", "")),
        template_id=str(raw.get("template_id") or DEFAULT_TEMPLATE_ID),
        signature_id=str(raw.get("signature_id") or DEFAULT_SIGNATURE_ID),
        sms_mode=sms_mode,  # type: ignore[arg-type]
    )


@dataclass(frozen=True)
class Trip:
    id: str
    name: str
    departure_date: date
    tags: tuple[str, ...]
    leader_name: str
    weather: str
    today_activity: str
    temperature: str


@dataclass(frozen=True)
class User:
    id: str
    name: str
    phone: str
    trip_id: str


@dataclass(frozen=True)
class SmsRule:
    id: str
    trigger_type: str
    trigger_time: str
    enabled: bool


@dataclass(frozen=True)
class Target:
    id: str
    target_type: str
    target_value: str


@dataclass(frozen=True)
class Campaign:
    id: str
    template: str
    target: Target
    template_id: str
    signature_id: str = DEFAULT_SIGNATURE_ID
    rule_ids: tuple[str, ...] = ("*",)


@dataclass(frozen=True)
class SmsData:
    trips: list[Trip]
    users: list[User]
    sms_rules: list[SmsRule]
    campaigns: list[Campaign]


class SmsService:
    """Provider boundary. Replace only Baidu branch for real SMS delivery."""

    def __init__(self, config: SmsConfig | None = None) -> None:
        self.config = config or SmsConfig()

    def send_sms(self, phone: str, template_id: str, params: dict[str, Any]) -> None:
        effective_template_id = template_id or self.config.template_id
        effective_signature_id = str(params.get("signature_id") or self.config.signature_id)
        params = {**params, "signature_id": effective_signature_id}

        if self.config.sms_mode == "mock":
            logger.info(
                "Mock SMS sent to %s: template_id=%s signature_id=%s params=%s",
                phone,
                effective_template_id,
                effective_signature_id,
                params,
            )
            print(f"Mock SMS sent to {phone}: {params}")
            return

        self._send_baidu_sms(phone, effective_template_id, effective_signature_id, params)

    def _send_baidu_sms(
        self,
        phone: str,
        template_id: str,
        signature_id: str,
        params: dict[str, Any],
    ) -> None:
        # TODO: 使用 AK/SK 接入百度云短信。
        # Required values are available from self.config.ak/self.config.sk,
        # template_id, signature_id, phone and params.
        raise NotImplementedError("Baidu SMS API call is not implemented yet")


class SmsSendLogStore:
    """SQLite-backed send log used for idempotency and traceability."""

    def __init__(self, db_path: str | Path = DEFAULT_SMS_LOG_DB_PATH) -> None:
        self.db_path = str(db_path)
        self._lock = Lock()
        self._conn = sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sms_send_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    trip_id TEXT NOT NULL,
                    rule_id TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    content TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('success', 'failed')),
                    send_time TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_sms_send_log_success_idempotency
                ON sms_send_log (user_id, rule_id, substr(send_time, 1, 10))
                WHERE status = 'success'
                """
            )
            self._conn.commit()

    def already_sent(self, user_id: str, rule_id: str, send_date: date) -> bool:
        with self._lock:
            return self._already_sent_locked(user_id, rule_id, send_date)

    def send_once(
        self,
        sms_service: SmsService,
        phone: str,
        template_id: str,
        params: dict[str, Any],
        send_at: datetime,
    ) -> SmsSendStatus:
        user_id = str(params["user_id"])
        trip_id = str(params["trip_id"])
        rule_id = str(params["rule_id"])
        content = str(params["message"])
        send_time = send_at.isoformat(timespec="seconds")

        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                if self._already_sent_locked(user_id, rule_id, send_at.date()):
                    self._conn.commit()
                    logger.info(
                        "Skip duplicate SMS: user_id=%s rule_id=%s date=%s",
                        user_id,
                        rule_id,
                        send_at.date().isoformat(),
                    )
                    return "skipped"

                try:
                    sms_service.send_sms(phone, template_id, params)
                except Exception:
                    self._insert_log_locked(
                        user_id=user_id,
                        trip_id=trip_id,
                        rule_id=rule_id,
                        phone=phone,
                        content=content,
                        status="failed",
                        send_time=send_time,
                    )
                    self._conn.commit()
                    logger.exception(
                        "SMS send failed: user_id=%s trip_id=%s rule_id=%s phone=%s",
                        user_id,
                        trip_id,
                        rule_id,
                        phone,
                    )
                    return "failed"

                self._insert_log_locked(
                    user_id=user_id,
                    trip_id=trip_id,
                    rule_id=rule_id,
                    phone=phone,
                    content=content,
                    status="success",
                    send_time=send_time,
                )
                self._conn.commit()
                return "success"
            except Exception:
                self._conn.rollback()
                raise

    def count_logs(self, status: str | None = None) -> int:
        with self._lock:
            if status is None:
                row = self._conn.execute("SELECT COUNT(*) AS count FROM sms_send_log").fetchone()
            else:
                row = self._conn.execute(
                    "SELECT COUNT(*) AS count FROM sms_send_log WHERE status = ?",
                    (status,),
                ).fetchone()
            return int(row["count"])

    def list_logs(self, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 500))
        with self._lock:
            if status is None:
                rows = self._conn.execute(
                    """
                    SELECT id, user_id, trip_id, rule_id, phone, content, status, send_time
                    FROM sms_send_log
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (safe_limit,),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    """
                    SELECT id, user_id, trip_id, rule_id, phone, content, status, send_time
                    FROM sms_send_log
                    WHERE status = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (status, safe_limit),
                ).fetchall()
            return [dict(row) for row in rows]

    def list_failed_logs(self, limit: int = 100) -> list[dict[str, Any]]:
        return self.list_logs(status="failed", limit=limit)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _already_sent_locked(self, user_id: str, rule_id: str, send_date: date) -> bool:
        row = self._conn.execute(
            """
            SELECT id
            FROM sms_send_log
            WHERE user_id = ?
              AND rule_id = ?
              AND substr(send_time, 1, 10) = ?
              AND status = 'success'
            LIMIT 1
            """,
            (user_id, rule_id, send_date.isoformat()),
        ).fetchone()
        return row is not None

    def _insert_log_locked(
        self,
        *,
        user_id: str,
        trip_id: str,
        rule_id: str,
        phone: str,
        content: str,
        status: Literal["success", "failed"],
        send_time: str,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO sms_send_log (
                user_id, trip_id, rule_id, phone, content, status, send_time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, trip_id, rule_id, phone, content, status, send_time),
        )


def render_template(template: str, data: dict[str, Any]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        return str(data.get(key, match.group(0)))

    return TEMPLATE_PATTERN.sub(replace, template)


def parse_hhmm(value: str) -> clock_time:
    hour, minute = value.split(":", maxsplit=1)
    return clock_time(hour=int(hour), minute=int(minute))


def parse_departure_offset(value: str) -> tuple[int, clock_time]:
    offset_part, send_time_part = value.split(maxsplit=1)
    return int(offset_part.removesuffix("d")), parse_hhmm(send_time_part)


def build_demo_data(today: date | None = None) -> SmsData:
    current_date = today or date.today()

    trips = [
        Trip(
            id="trip-japan-sakura",
            name="日本樱花购物团",
            departure_date=current_date + timedelta(days=3),
            tags=("Japan", "shopping", "sakura"),
            leader_name="张导",
            weather="东京 多云",
            today_activity="浅草寺参观与银座购物",
            temperature="18°C",
        ),
        Trip(
            id="trip-africa-adventure",
            name="非洲肯尼亚探险团",
            departure_date=current_date + timedelta(days=1),
            tags=("Africa", "adventure", "safety", "high_altitude"),
            leader_name="李导",
            weather="内罗毕 晴",
            today_activity="草原巡游与安全讲解",
            temperature="27°C",
        ),
        Trip(
            id="trip-europe-luxury",
            name="欧洲奢华退税团",
            departure_date=current_date + timedelta(days=3),
            tags=("Europe", "luxury", "tax_refund", "horse_riding"),
            leader_name="王导",
            weather="巴黎 小雨",
            today_activity="卢浮宫参观与精品店退税说明",
            temperature="12°C",
        ),
    ]

    users = [
        User(id="u-jp-001", name="陈一", phone="13800001001", trip_id="trip-japan-sakura"),
        User(id="u-jp-002", name="周二", phone="13800001002", trip_id="trip-japan-sakura"),
        User(id="u-af-001", name="赵三", phone="13800002001", trip_id="trip-africa-adventure"),
        User(id="u-af-002", name="钱四", phone="13800002002", trip_id="trip-africa-adventure"),
        User(id="u-eu-001", name="孙五", phone="13800003001", trip_id="trip-europe-luxury"),
        User(id="u-eu-002", name="吴六", phone="13800003002", trip_id="trip-europe-luxury"),
    ]

    sms_rules = [
        SmsRule(id="departure_minus_3", trigger_type="departure_offset", trigger_time="-3d 09:00", enabled=True),
        SmsRule(id="departure_minus_1", trigger_type="departure_offset", trigger_time="-1d 18:00", enabled=True),
        SmsRule(id="daily_0700", trigger_type="daily", trigger_time="07:00", enabled=True),
        SmsRule(id="daily_1200", trigger_type="daily", trigger_time="12:00", enabled=True),
        SmsRule(id="daily_2000", trigger_type="daily", trigger_time="20:00", enabled=True),
        SmsRule(id="special_horse_riding", trigger_type="special_tag", trigger_time="horse_riding", enabled=True),
        SmsRule(id="special_high_altitude", trigger_type="special_tag", trigger_time="high_altitude", enabled=True),
    ]

    japan = Target(id="target-japan", target_type="tag", target_value="Japan")
    africa = Target(id="target-africa", target_type="tag", target_value="Africa")
    europe = Target(id="target-europe", target_type="tag", target_value="Europe")
    horse_riding = Target(id="target-horse-riding", target_type="tag", target_value="horse_riding")
    high_altitude = Target(id="target-high-altitude", target_type="tag", target_value="high_altitude")

    campaigns = [
        Campaign(
            id="japan_pre_3",
            target=japan,
            rule_ids=("departure_minus_3",),
            template_id="tpl-japan-pre-3",
            template="【{{trip_name}}】{{user_name}}您好，出发前3天提醒：导游{{leader_name}}，请准备赏樱服装与购物清单。",
        ),
        Campaign(
            id="japan_pre_1",
            target=japan,
            rule_ids=("departure_minus_1",),
            template_id="tpl-japan-pre-1",
            template="【{{trip_name}}】明日出发：{{weather}}，{{temperature}}。请确认护照、日元现金和集合时间。",
        ),
        Campaign(
            id="japan_morning",
            target=japan,
            rule_ids=("daily_0700",),
            template_id="tpl-japan-morning",
            template="早安，{{user_name}}！今日日本行程：{{today_activity}}，天气{{weather}}，温度{{temperature}}。",
        ),
        Campaign(
            id="japan_noon",
            target=japan,
            rule_ids=("daily_1200",),
            template_id="tpl-japan-noon",
            template="午间提醒：银座购物时请保留小票，导游{{leader_name}}将协助退税与集合。",
        ),
        Campaign(
            id="japan_night",
            target=japan,
            rule_ids=("daily_2000",),
            template_id="tpl-japan-night",
            template="晚间提醒：明日樱花点位以{{leader_name}}通知为准，请提前给手机充电。",
        ),
        Campaign(
            id="africa_pre_3",
            target=africa,
            rule_ids=("departure_minus_3",),
            template_id="tpl-africa-pre-3",
            template="【{{trip_name}}】出发前3天安全提示：请准备防晒、防蚊和探险装备，导游{{leader_name}}。",
        ),
        Campaign(
            id="africa_pre_1",
            target=africa,
            rule_ids=("departure_minus_1",),
            template_id="tpl-africa-pre-1",
            template="【{{trip_name}}】明日出发：{{weather}}，{{temperature}}。请确认疫苗证明和保险材料。",
        ),
        Campaign(
            id="africa_morning",
            target=africa,
            rule_ids=("daily_0700",),
            template_id="tpl-africa-morning",
            template="早安！今日非洲探险安排：{{today_activity}}。请听从{{leader_name}}安全指引。",
        ),
        Campaign(
            id="africa_noon",
            target=africa,
            rule_ids=("daily_1200",),
            template_id="tpl-africa-noon",
            template="午间安全提醒：天气{{weather}}，温度{{temperature}}，请补水并避免单独行动。",
        ),
        Campaign(
            id="africa_night",
            target=africa,
            rule_ids=("daily_2000",),
            template_id="tpl-africa-night",
            template="晚间提醒：请检查明日装备，贵重物品随身携带，紧急联系{{leader_name}}。",
        ),
        Campaign(
            id="europe_pre_3",
            target=europe,
            rule_ids=("departure_minus_3",),
            template_id="tpl-europe-pre-3",
            template="【{{trip_name}}】出发前3天提醒：请准备正装、信用卡和退税资料，导游{{leader_name}}。",
        ),
        Campaign(
            id="europe_pre_1",
            target=europe,
            rule_ids=("departure_minus_1",),
            template_id="tpl-europe-pre-1",
            template="【{{trip_name}}】明日出发：{{weather}}，{{temperature}}。请确认申根材料与航班集合点。",
        ),
        Campaign(
            id="europe_morning",
            target=europe,
            rule_ids=("daily_0700",),
            template_id="tpl-europe-morning",
            template="早安！今日欧洲行程：{{today_activity}}。请关注奢华购物与退税说明。",
        ),
        Campaign(
            id="europe_noon",
            target=europe,
            rule_ids=("daily_1200",),
            template_id="tpl-europe-noon",
            template="午间提醒：精品店购物请索取退税单，导游{{leader_name}}将在集合时统一核对。",
        ),
        Campaign(
            id="europe_night",
            target=europe,
            rule_ids=("daily_2000",),
            template_id="tpl-europe-night",
            template="晚间提醒：请整理今日票据和退税单，明日集合以{{leader_name}}通知为准。",
        ),
        Campaign(
            id="special_horse_riding_safety",
            target=horse_riding,
            rule_ids=("special_horse_riding",),
            template_id="tpl-special-horse-riding",
            template="特殊场景提醒：{{user_name}}，今日含骑马体验，请佩戴护具并听从工作人员安排。",
        ),
        Campaign(
            id="special_high_altitude_safety",
            target=high_altitude,
            rule_ids=("special_high_altitude",),
            template_id="tpl-special-high-altitude",
            template="特殊场景提醒：{{user_name}}，当前行程涉及高原，请慢行、补水，如不适立即联系{{leader_name}}。",
        ),
    ]

    return SmsData(trips=trips, users=users, sms_rules=sms_rules, campaigns=campaigns)


def users_for_trip(data: SmsData, trip_id: str) -> list[User]:
    return [user for user in data.users if user.trip_id == trip_id]


def target_matches_trip(target: Target, trip: Trip) -> bool:
    if target.target_type == "all":
        return True
    if target.target_type == "tag":
        return target.target_value in trip.tags
    return False


def campaign_matches_rule(campaign: Campaign, rule: SmsRule) -> bool:
    return "*" in campaign.rule_ids or rule.id in campaign.rule_ids


def match_campaigns(trip: Trip, rule: SmsRule, campaigns: list[Campaign]) -> list[Campaign]:
    return [
        campaign
        for campaign in campaigns
        if campaign_matches_rule(campaign, rule) and target_matches_trip(campaign.target, trip)
    ]


def rule_applies_to_trip(rule: SmsRule, trip: Trip, current_at: datetime) -> bool:
    if not rule.enabled:
        return False

    if rule.trigger_type == "departure_offset":
        offset_days, _ = parse_departure_offset(rule.trigger_time)
        return current_at.date() == trip.departure_date + timedelta(days=offset_days)

    if rule.trigger_type == "daily":
        return True

    if rule.trigger_type == "special_tag":
        return rule.trigger_time in trip.tags

    return False


def template_data(trip: Trip, user: User, rule: SmsRule, campaign: Campaign) -> dict[str, Any]:
    return {
        "trip_id": trip.id,
        "trip_name": trip.name,
        "departure_date": trip.departure_date.isoformat(),
        "tags": list(trip.tags),
        "leader_name": trip.leader_name,
        "weather": trip.weather,
        "today_activity": trip.today_activity,
        "temperature": trip.temperature,
        "user_id": user.id,
        "user_name": user.name,
        "rule_id": rule.id,
        "campaign_id": campaign.id,
    }


def _send_prepared_sms(
    *,
    sms_service: SmsService,
    log_store: SmsSendLogStore,
    phone: str,
    template_id: str,
    params: dict[str, Any],
    send_at: datetime,
) -> SmsSendStatus:
    return log_store.send_once(
        sms_service=sms_service,
        phone=phone,
        template_id=template_id,
        params=params,
        send_at=send_at,
    )


def process_rule(
    data: SmsData,
    rule: SmsRule,
    sms_service: SmsService,
    log_store: SmsSendLogStore,
    current_at: datetime | None = None,
    force: bool = False,
) -> int:
    send_at = current_at or datetime.now()
    success_count = 0
    skipped_count = 0
    failed_count = 0

    for trip in data.trips:
        if not force and not rule_applies_to_trip(rule, trip, send_at):
            continue

        matched_campaigns = match_campaigns(trip, rule, data.campaigns)
        if not matched_campaigns:
            logger.info("No campaign matched: rule=%s trip=%s", rule.id, trip.id)
            continue

        for user in users_for_trip(data, trip.id):
            for campaign in matched_campaigns:
                params = template_data(trip, user, rule, campaign)
                params["signature_id"] = campaign.signature_id
                params["message"] = render_template(campaign.template, params)
                status = _send_prepared_sms(
                    sms_service=sms_service,
                    log_store=log_store,
                    phone=user.phone,
                    template_id=campaign.template_id,
                    params=params,
                    send_at=send_at,
                )
                if status == "success":
                    success_count += 1
                elif status == "failed":
                    failed_count += 1
                else:
                    skipped_count += 1

    logger.info(
        "Rule %s finished, success_count=%s failed_count=%s skipped_count=%s",
        rule.id,
        success_count,
        failed_count,
        skipped_count,
    )
    return success_count


def retry_failed_sms(
    log_store: SmsSendLogStore,
    sms_service: SmsService,
    limit: int = 100,
    retry_at: datetime | None = None,
) -> dict[str, int]:
    attempted = 0
    success = 0
    failed = 0
    skipped = 0
    send_at = retry_at or datetime.now()

    for log in log_store.list_failed_logs(limit=limit):
        params = {
            "user_id": log["user_id"],
            "trip_id": log["trip_id"],
            "rule_id": log["rule_id"],
            "campaign_id": "retry",
            "message": log["content"],
            "signature_id": sms_service.config.signature_id,
            "retry_from_log_id": log["id"],
        }
        attempted += 1
        status = _send_prepared_sms(
            sms_service=sms_service,
            log_store=log_store,
            phone=str(log["phone"]),
            template_id=sms_service.config.template_id,
            params=params,
            send_at=send_at,
        )
        if status == "success":
            success += 1
        elif status == "failed":
            failed += 1
        else:
            skipped += 1

    return {"attempted": attempted, "success": success, "failed": failed, "skipped": skipped}


def schedule_sms_jobs(
    scheduler: BackgroundScheduler,
    data: SmsData,
    sms_service: SmsService,
    log_store: SmsSendLogStore,
) -> None:
    now = datetime.now()

    for rule in data.sms_rules:
        if not rule.enabled:
            continue

        if rule.trigger_type == "departure_offset":
            scheduled_dates: set[datetime] = set()
            offset_days, send_time = parse_departure_offset(rule.trigger_time)
            for trip in data.trips:
                intended_at = datetime.combine(trip.departure_date + timedelta(days=offset_days), send_time)
                if intended_at <= now:
                    logger.info(
                        "Skip expired schedule: rule=%s trip=%s intended_at=%s",
                        rule.id,
                        trip.id,
                        intended_at.isoformat(timespec="seconds"),
                    )
                    continue
                if intended_at in scheduled_dates:
                    continue
                scheduled_dates.add(intended_at)
                scheduler.add_job(
                    process_rule,
                    trigger="date",
                    run_date=intended_at,
                    args=[data, rule, sms_service, log_store, intended_at],
                    id=f"rule:{rule.id}:{intended_at.isoformat()}",
                    replace_existing=True,
                )
                logger.info("Scheduled %s for %s", rule.id, intended_at.isoformat(timespec="seconds"))
            continue

        if rule.trigger_type == "daily":
            send_time = parse_hhmm(rule.trigger_time)
            scheduler.add_job(
                process_rule,
                trigger="cron",
                hour=send_time.hour,
                minute=send_time.minute,
                args=[data, rule, sms_service, log_store],
                id=f"rule:{rule.id}",
                replace_existing=True,
            )
            logger.info("Scheduled %s daily at %s", rule.id, rule.trigger_time)
            continue

        if rule.trigger_type == "special_tag":
            scheduler.add_job(
                process_rule,
                trigger="date",
                run_date=now + timedelta(seconds=1),
                args=[data, rule, sms_service, log_store, now],
                id=f"rule:{rule.id}:demo",
                replace_existing=True,
            )
            logger.info("Scheduled special tag demo %s for tag=%s", rule.id, rule.trigger_time)
            continue

        logger.warning("Unknown trigger_type=%s for rule=%s", rule.trigger_type, rule.id)


def run_once(data: SmsData, sms_service: SmsService, log_store: SmsSendLogStore) -> None:
    for rule in data.sms_rules:
        process_rule(data, rule, sms_service, log_store, force=True)


class TriggerSmsRequest(BaseModel):
    rule_id: str | None = None
    force: bool = True


class RetrySmsRequest(BaseModel):
    limit: int = 100


def create_api_app(
    data: SmsData | None = None,
    sms_service: SmsService | None = None,
    log_store: SmsSendLogStore | None = None,
) -> FastAPI:
    app = FastAPI(title="Travel SMS API")
    app.state.sms_data = data or build_demo_data()
    app.state.sms_service = sms_service or SmsService(load_sms_config())
    app.state.sms_log_store = log_store or SmsSendLogStore()

    @app.post("/trigger-sms")
    def trigger_sms(request: TriggerSmsRequest) -> dict[str, Any]:
        rules = app.state.sms_data.sms_rules
        if request.rule_id:
            rules = [rule for rule in rules if rule.id == request.rule_id]
            if not rules:
                return {"ok": False, "error": "rule_id not found", "sent": 0}

        sent_by_rule: dict[str, int] = {}
        total_sent = 0
        for rule in rules:
            sent = process_rule(
                app.state.sms_data,
                rule,
                app.state.sms_service,
                app.state.sms_log_store,
                force=request.force,
            )
            sent_by_rule[rule.id] = sent
            total_sent += sent

        return {
            "ok": True,
            "sent": total_sent,
            "sent_by_rule": sent_by_rule,
            "success_logs": app.state.sms_log_store.count_logs("success"),
            "failed_logs": app.state.sms_log_store.count_logs("failed"),
        }

    @app.get("/sms-logs")
    def sms_logs(
        status: str | None = Query(default=None, pattern="^(success|failed)$"),
        limit: int = Query(default=100, ge=1, le=500),
    ) -> dict[str, Any]:
        return {
            "ok": True,
            "logs": app.state.sms_log_store.list_logs(status=status, limit=limit),
        }

    @app.post("/retry-failed-sms")
    def retry_failed(request: RetrySmsRequest) -> dict[str, Any]:
        result = retry_failed_sms(
            app.state.sms_log_store,
            app.state.sms_service,
            limit=request.limit,
        )
        return {"ok": True, **result}

    return app


def app() -> FastAPI:
    return create_api_app()


def main() -> None:
    parser = argparse.ArgumentParser(description="Commercial-ready mock SMS scheduler")
    parser.add_argument("--run-once", action="store_true", help="send all demo rules immediately and exit")
    parser.add_argument("--api", action="store_true", help="run minimal FastAPI SMS API")
    parser.add_argument("--host", default="127.0.0.1", help="API host when --api is used")
    parser.add_argument("--port", type=int, default=8001, help="API port when --api is used")
    parser.add_argument("--demo-seconds", type=int, default=0, help="run scheduler for N seconds then exit")
    parser.add_argument(
        "--sms-log-db",
        default=str(DEFAULT_SMS_LOG_DB_PATH),
        help="SQLite DB path for sms_send_log idempotency records",
    )
    parser.add_argument("--config", default="", help="optional JSON config path for SMS settings")
    args = parser.parse_args()

    config = load_sms_config(args.config or None)
    data = build_demo_data()
    sms_service = SmsService(config)
    log_store = SmsSendLogStore(args.sms_log_db)

    if args.api:
        import uvicorn

        api_app = create_api_app(data=data, sms_service=sms_service, log_store=log_store)
        uvicorn.run(api_app, host=args.host, port=args.port)
        log_store.close()
        return

    if args.run_once:
        run_once(data, sms_service, log_store)
        log_store.close()
        return

    scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    schedule_sms_jobs(scheduler, data, sms_service, log_store)
    scheduler.start()
    logger.info("SMS scheduler started. Press Ctrl+C to stop.")

    try:
        if args.demo_seconds > 0:
            time.sleep(args.demo_seconds)
        else:
            while True:
                time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Stopping SMS scheduler.")
    finally:
        scheduler.shutdown(wait=False)
        log_store.close()


if __name__ == "__main__":
    main()
