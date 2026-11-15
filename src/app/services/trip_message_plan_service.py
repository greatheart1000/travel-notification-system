from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.services.reminder_suggestion_service import region_guidance

SLOT_TIMES: tuple[tuple[str, str, str], ...] = (
    ("morning", "07:00", "早间"),
    ("afternoon", "12:30", "午间"),
    ("evening", "20:00", "晚间"),
)

STAGE_LABELS = {
    "pre_trip": "行前",
    "in_trip": "行中",
    "post_trip": "行后",
}


def _parse_date(raw: Any) -> date | None:
    value = str(raw or "").strip()[:10]
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _day_for(trip: dict[str, Any], target: str) -> dict[str, Any] | None:
    itinerary = [item for item in (trip.get("itinerary") or []) if isinstance(item, dict)]
    return next(
        (item for item in itinerary if str(item.get("date") or "")[:10] == target),
        None,
    )


def _activity(day: dict[str, Any] | None) -> str:
    if not day:
        return ""
    return str(
        day.get("activity") or day.get("title") or day.get("route") or ""
    ).strip()


def _hotel(day: dict[str, Any] | None) -> str:
    return str((day or {}).get("hotel") or "").strip()


def _slot_for_hour(hour: int) -> str:
    if hour < 11:
        return "morning"
    if hour < 17:
        return "afternoon"
    return "evening"


def _attempt_indexes(
    attempts: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    by_schedule: dict[str, dict[str, Any]] = {}
    by_slot: dict[tuple[str, str], dict[str, Any]] = {}
    for item in attempts:
        schedule_key = str(item.get("schedule_key") or "")
        if schedule_key:
            current = by_schedule.get(schedule_key)
            if current is None or (not current.get("ok") and item.get("ok")):
                by_schedule[schedule_key] = item
        raw = str(item.get("attempted_at") or "")
        if len(raw) < 13:
            continue
        try:
            hour = datetime.fromisoformat(raw.replace("Z", "+00:00")).hour
        except ValueError:
            continue
        key = (raw[:10], _slot_for_hour(hour))
        current = by_slot.get(key)
        if current is None or (not current.get("ok") and item.get("ok")):
            by_slot[key] = item
    return by_schedule, by_slot


def _pick_rule(rules: list[dict[str, Any]], stage: str, slot: str) -> dict[str, Any] | None:
    candidates = [
        rule
        for rule in rules
        if str(rule.get("stage") or "") == stage
        and str(rule.get("scene") or "normal") == "normal"
        and str(rule.get("time_slot") or "") in {slot, "all_day"}
        and bool(rule.get("enabled", True))
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: int(item.get("priority", 100)))[0]


def _render_template(
    template_service: Any,
    rule: dict[str, Any] | None,
    variables: dict[str, Any],
    tenant_id: str,
    month: int,
) -> tuple[str, str]:
    if not rule or not rule.get("template_id"):
        return "", ""
    template = template_service.get_notification_template(
        str(rule.get("template_id")), tenant_id=tenant_id
    )
    if template is None:
        return "", ""
    if hasattr(template_service, "resolve_seasonal_template"):
        template = template_service.resolve_seasonal_template(
            template, tenant_id=tenant_id, month=month
        )
    try:
        return template_service.render_notification(template, variables), template.id
    except ValueError:
        return "", template.id


def _base_content(
    *,
    stage: str,
    slot: str,
    day: date,
    trip: dict[str, Any],
    today: date,
    weather_text: str,
) -> tuple[str, str]:
    destination = str(trip.get("destination") or "本次行程")
    region_tip = region_guidance(destination)
    itinerary_day = _day_for(trip, day.isoformat())
    activity = _activity(itinerary_day)
    hotel = _hotel(itinerary_day)
    start = _parse_date(trip.get("start_date"))
    end = _parse_date(trip.get("end_date"))

    if stage == "pre_trip":
        days = (start - today).days if start else 0
        first_day = _day_for(trip, start.isoformat()) if start else None
        first_activity = _activity(first_day)
        if slot == "morning" and days >= 2:
            title = "行前准备提醒"
            content = (
                f"【行前提醒】{destination}行程将于 {start.isoformat() if start else ''} 出发，"
                f"还有 {days} 天。"
                + (f"首日安排：{first_activity}。" if first_activity else "")
                + f"请提前整理证件与行李，保持手机畅通。{region_tip}"
            )
        else:
            title = "行前最终确认"
            content = (
                f"【行前确认】{destination}行程明天出发。"
                "请再次确认身份证件、集合时间和航班信息，今晚早点休息。"
                + (f"首日安排：{first_activity}。" if first_activity else "")
                + region_tip
            )
        return title, content

    if stage == "post_trip":
        return (
            "行程回访",
            f"【行程回访】{destination}行程已经结束，感谢大家的信任与配合。"
            "欢迎在群里分享旅途照片和感受，也欢迎提出宝贵建议。",
        )

    if slot == "morning":
        return (
            "今日早间提醒",
            f"【早安】各位团友，{destination}，{day.isoformat()}。"
            + (f"今日安排：{activity}。" if activity else "")
            + (f"当前天气：{weather_text}。" if weather_text and day == today else "")
            + f"请按约定时间集合，带好证件和随身物品。{region_tip}",
        )
    if slot == "afternoon":
        return (
            "午间安全提醒",
            f"【午间提醒】各位团友，中午好。"
            + (f"当前天气：{weather_text}。" if weather_text and day == today else "")
            + "请注意补水、防晒和休息，用餐后按约定时间集合。"
            + region_tip,
        )
    next_day = _day_for(trip, (day + timedelta(days=1)).isoformat())
    next_activity = _activity(next_day)
    return (
        "晚间次日预告",
        f"【晚间播报】各位团友，今天的行程辛苦了。"
        + (f"明日安排：{next_activity}。" if next_activity else "")
        + (f"今晚入住：{hotel}。" if hotel else "")
        + "请早点休息，明日集合时间与天气变化以群内通知为准。"
        + region_tip,
    )


def build_trip_message_plan(
    *,
    trip: dict[str, Any],
    rules: list[dict[str, Any]],
    template_service: Any,
    attempts: list[dict[str, Any]],
    today: date | None = None,
    weather_text: str = "",
) -> list[dict[str, Any]]:
    now = today or datetime.now(tz=ZoneInfo("Asia/Shanghai")).date()
    tenant_id = str(trip.get("tenant_id") or "")
    start = _parse_date(trip.get("start_date"))
    end = _parse_date(trip.get("end_date"))
    if start is None or end is None:
        return []
    by_schedule, by_slot = _attempt_indexes(attempts)
    items: list[dict[str, Any]] = []

    def append_item(
        *,
        item_date: date,
        stage: str,
        slot: str,
        time_text: str,
        title: str,
        content: str,
        template_id: str = "",
        rule_id: str = "",
    ) -> None:
        item_id = f"{trip.get('id', '')}:{item_date.isoformat()}:{stage}:{slot}"
        key = (item_date.isoformat(), slot)
        attempt = by_schedule.get(item_id) or by_slot.get(key)
        if attempt is not None:
            status = "sent" if attempt.get("ok") else "failed"
        elif item_date < now:
            status = "missed"
        else:
            status = "pending"
        items.append(
            {
                "id": item_id,
                "date": item_date.isoformat(),
                "time": time_text,
                "slot": slot,
                "slot_label": next(label for key_slot, _, label in SLOT_TIMES if key_slot == slot),
                "stage": stage,
                "stage_label": STAGE_LABELS.get(stage, stage),
                "title": title,
                "content": content,
                "template_id": template_id,
                "rule_id": rule_id,
                "status": status,
                "can_send": item_date >= now,
            }
        )

    # 行前 3 天 / 1 天
    for offset, slot, time_text in ((3, "morning", "07:00"), (1, "evening", "20:00")):
        item_date = start - timedelta(days=offset)
        rule = _pick_rule(rules, "pre_trip", slot)
        title, base = _base_content(
            stage="pre_trip",
            slot=slot,
            day=item_date,
            trip=trip,
            today=now,
            weather_text=weather_text,
        )
        variables = {
            "customer_name": "各位团友",
            "destination": str(trip.get("destination") or ""),
            "departure_date": start.isoformat(),
            "trip_date": item_date.isoformat(),
            "weather_text": weather_text,
            "alert_title": "",
            "flight_info": "请确认航班信息",
            "highlight": _activity(_day_for(trip, start.isoformat())),
            "climate": weather_text,
            "dress_code": "请按当地温度增减衣物",
            "packing_tip": "建议携带雨具和保暖外套",
            "concierge_name": "管家",
            "contact_phone": str(trip.get("contact_phone") or ""),
            "time_slot": time_text,
        }
        rendered, template_id = _render_template(
            template_service, rule, variables, tenant_id, item_date.month
        )
        first_activity = _activity(_day_for(trip, start.isoformat()))
        if rendered:
            days_until = (start - item_date).days
            lead = (
                f"{trip.get('destination') or '本次行程'}行程将于 {start.isoformat()} 出发，"
                f"还有 {days_until} 天。"
                if offset == 3
                else f"{trip.get('destination') or '本次行程'}行程将于 {start.isoformat()} 出发。"
            )
            rendered = f"{lead}{rendered}"
        if rendered and first_activity and first_activity not in rendered:
            rendered = f"{rendered}\n首日安排：{first_activity}。"
        append_item(
            item_date=item_date,
            stage="pre_trip",
            slot=slot,
            time_text=time_text,
            title=str((rule or {}).get("name") or title),
            content=rendered or base,
            template_id=template_id,
            rule_id=str((rule or {}).get("id") or ""),
        )

    # 行中每天
    cursor = start
    while cursor <= end:
        for slot, time_text, _ in SLOT_TIMES:
            rule = _pick_rule(rules, "in_trip", slot)
            title, base = _base_content(
                stage="in_trip",
                slot=slot,
                day=cursor,
                trip=trip,
                today=now,
                weather_text=weather_text,
            )
            day = _day_for(trip, cursor.isoformat())
            variables = {
                "customer_name": "各位团友",
                "destination": str(trip.get("destination") or ""),
                "departure_date": start.isoformat(),
                "trip_date": cursor.isoformat(),
                "weather_text": weather_text,
                "alert_title": "",
                "flight_info": "",
                "highlight": _activity(day),
                "climate": weather_text,
                "dress_code": "请按当地温度增减衣物",
                "packing_tip": "建议携带雨具和保暖外套",
                "concierge_name": "管家",
                "contact_phone": str(trip.get("contact_phone") or ""),
                "time_slot": time_text,
                "next_day_highlight": _activity(
                    _day_for(trip, (cursor + timedelta(days=1)).isoformat())
                ),
                "next_day_weather": weather_text,
            }
            rendered, template_id = _render_template(
                template_service, rule, variables, tenant_id, cursor.month
            )
            if rendered:
                if slot in {"morning", "afternoon"} and _activity(day) and _activity(day) not in rendered:
                    rendered = f"{rendered}\n今日安排：{_activity(day)}。"
                if slot == "evening":
                    next_activity = _activity(
                        _day_for(trip, (cursor + timedelta(days=1)).isoformat())
                    )
                    if next_activity and next_activity not in rendered:
                        rendered = f"{rendered}\n明日安排：{next_activity}。"
            append_item(
                item_date=cursor,
                stage="in_trip",
                slot=slot,
                time_text=time_text,
                title=str((rule or {}).get("name") or title),
                content=rendered or base,
                template_id=template_id,
                rule_id=str((rule or {}).get("id") or ""),
            )
        cursor += timedelta(days=1)

    # 行后回访
    rule = _pick_rule(rules, "post_trip", "evening")
    title, base = _base_content(
        stage="post_trip",
        slot="evening",
        day=end,
        trip=trip,
        today=now,
        weather_text=weather_text,
    )
    variables = {
        "customer_name": "各位团友",
        "destination": str(trip.get("destination") or ""),
        "departure_date": start.isoformat(),
        "trip_date": end.isoformat(),
        "weather_text": weather_text,
        "alert_title": "",
        "flight_info": "",
        "highlight": "",
        "climate": weather_text,
        "dress_code": "",
        "packing_tip": "",
        "concierge_name": "管家",
        "contact_phone": str(trip.get("contact_phone") or ""),
        "time_slot": "20:00",
    }
    rendered, template_id = _render_template(
        template_service, rule, variables, tenant_id, end.month
    )
    append_item(
        item_date=end,
        stage="post_trip",
        slot="evening",
        time_text="20:30",
        title=str((rule or {}).get("name") or title),
        content=rendered or base,
        template_id=template_id,
        rule_id=str((rule or {}).get("id") or ""),
    )

    items.sort(key=lambda item: (item["date"], item["time"]))
    return items
