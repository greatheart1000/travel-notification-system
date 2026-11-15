from __future__ import annotations

import re
from datetime import date
from typing import Any

from app.modules.notification.concierge_playbook import MESSAGE_TEMPLATES

ROLE_LABELS = {
    "manager": "团期负责人",
    "concierge": "旅行管家",
    "driver": "司机",
}

ROLE_ALIASES = {
    "manager": ("manager", "计调", "负责人"),
    "concierge": ("concierge", "导游", "guide", "管家"),
    "driver": ("driver", "司机"),
}

SLOTS = (("morning", "07:00", "早间"), ("afternoon", "12:30", "午间"))


def season_for(month: int) -> str:
    if 3 <= month <= 5:
        return "spring"
    if 6 <= month <= 8:
        return "summer"
    if 9 <= month <= 10:
        return "autumn"
    return "winter"


def staff_variables(trip: dict[str, Any]) -> dict[str, str]:
    # Missing names must stay empty, not become "管家"/"司机": otherwise the
    # rendered copy reads "旅行管家管家" or "司机司机".
    return {
        "manager_name": str(trip.get("trip_manager_name") or trip.get("leader_name") or ""),
        "manager_phone": str(trip.get("trip_manager_phone") or trip.get("contact_phone") or ""),
        "concierge_name": str(trip.get("concierge_name") or ""),
        "concierge_phone": str(trip.get("concierge_phone") or trip.get("contact_phone") or ""),
        "driver_name": str(trip.get("driver_name") or ""),
        "driver_phone": str(trip.get("driver_phone") or ""),
    }


def render_role_content(trip: dict[str, Any], role: str, slot: str, month: int) -> str:
    # UI uses "afternoon"; the playbook template prefix is "noon".
    template_slot = "noon" if slot == "afternoon" else slot
    key = f"{template_slot}_{season_for(month)}_{role}"
    content = MESSAGE_TEMPLATES.get(key, "")
    if not content:
        return ""
    for name, value in staff_variables(trip).items():
        content = content.replace("{{" + name + "}}", value)
    # If a role has no phone configured, drop the empty parenthetical rather
    # than sending "（电话：）" to tourists.
    content = re.sub(r"（电话：\s*）", "", content)
    return content


def resolve_recipient(trip: dict[str, Any], role: str) -> dict[str, str]:
    role_recipients = trip.get("role_recipients")
    if not isinstance(role_recipients, dict):
        role_recipients = {}
    recipient = None
    for alias in ROLE_ALIASES.get(role, (role,)):
        if alias in role_recipients:
            recipient = role_recipients[alias]
            break
    if isinstance(recipient, str):
        value = recipient.strip()
        if value.startswith(("http://", "https://")):
            return {
                "channel": "wechat_work_group",
                "address": value,
                "label": "企业微信指定群",
            }
        if value:
            return {"channel": "sms", "address": value, "label": f"短信 {value}"}
    if isinstance(recipient, dict):
        raw_channel = str(recipient.get("channel") or "").strip().lower()
        address = str(recipient.get("address") or recipient.get("phone") or "").strip()
        if raw_channel in {"sms", "短信"}:
            channel = "sms"
        elif raw_channel:
            channel = "wechat_work_group"
        elif address and not address.startswith(("http://", "https://")):
            channel = "sms"
        else:
            channel = "wechat_work_group"
        if address:
            return {
                "channel": channel,
                "address": address,
                "label": "企业微信指定群" if channel == "wechat_work_group" else f"短信 {address}",
            }
    return {
        "channel": "wechat_work_group",
        "address": str(trip.get("webhook_url") or "").strip(),
        "label": "本团企业微信群",
    }


def build_staff_messages(
    trip: dict[str, Any],
    attempts: list[dict[str, Any]],
    *,
    today: date,
) -> list[dict[str, Any]]:
    attempt_by_schedule: dict[str, dict[str, Any]] = {}
    for attempt in attempts:
        schedule_key = str(attempt.get("schedule_key") or "")
        if not schedule_key:
            continue
        current = attempt_by_schedule.get(schedule_key)
        # Keep the first successful attempt; otherwise keep the most recent one.
        if current is None or (not current.get("ok") and attempt.get("ok")):
            attempt_by_schedule[schedule_key] = attempt
    items: list[dict[str, Any]] = []
    variables = staff_variables(trip)
    for role, role_label in ROLE_LABELS.items():
        recipient = resolve_recipient(trip, role)
        for slot, time_text, slot_label in SLOTS:
            schedule_key = f"{trip.get('id', '')}:{today.isoformat()}:staff:{role}:{slot}"
            attempt = attempt_by_schedule.get(schedule_key)
            status = (
                "sent"
                if attempt and attempt.get("ok")
                else "failed"
                if attempt
                else "pending"
            )
            rendered = render_role_content(trip, role, slot, today.month)
            # Show exactly what was sent, including a guide's manual edit.
            content = str((attempt or {}).get("content") or rendered)
            items.append(
                {
                    "id": schedule_key,
                    "role": role,
                    "role_label": role_label,
                    "name": variables.get(f"{role}_name", ""),
                    "phone": variables.get(f"{role}_phone", ""),
                    "slot": slot,
                    "time": time_text,
                    "slot_label": slot_label,
                    "title": f"{role_label} · {slot_label}",
                    "content": content,
                    "channel": recipient["channel"],
                    "channel_label": "企业微信" if recipient["channel"] == "wechat_work_group" else "短信",
                    "recipient_label": recipient["label"],
                    "status": status,
                }
            )
    return items
