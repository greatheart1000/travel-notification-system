"""工作流控制器 — HTTP 请求/响应处理, 调用 Service/DAO 层."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo
from typing import Any

from fastapi import Depends, HTTPException

from app.dao.repositories import (
    WorkflowExecutionRepository,
    TripStaffRepository,
    LifecyclePlaybookRepository,
)
from app.modules.integration.wechat_provider import WeChatWorkWebhookProvider
from app.modules.notification.concierge_playbook import MESSAGE_TEMPLATES
from app.models.dto.requests import (
    ResourceVerifyRequest,
    InsuranceVerifyRequest,
    BuildGroupRequest,
    TriggerSchedulerRequest,
    BatchSendWorkflowRequest,
)
from app.api.http import _template_cache, _workflow_cache, _staff_cache  # 性能优化：复用 TTL 缓存

UTC = UTC


# ── 内部辅助 ────────────────────────────────────────────────────────────

_WF_REPO_CACHE: dict[str, WorkflowExecutionRepository] = {}

def _get_wf_repo(store) -> WorkflowExecutionRepository:
    key = "default"
    if key not in _WF_REPO_CACHE:
        _WF_REPO_CACHE[key] = WorkflowExecutionRepository(store=store)
    return _WF_REPO_CACHE[key]


def _send_template(
    trip: dict[str, Any],
    template_key: str,
    *,
    store,
    preview: bool = False,
) -> tuple[bool, str]:
    """通用模板发送: 渲染 → 附加时间戳 → 推送（带缓存优化）。"""
    template_content = MESSAGE_TEMPLATES.get(template_key)
    if not template_content:
        raise HTTPException(status_code=500, detail=f"Template not found: {template_key}")

    trip_id = str(trip.get("id", ""))
    # 缓存 key: 模板+行程ID（避免每次重建staff_map和变量替换）
    cache_key = f"render:{template_key}:{trip_id}"
    if not preview:
        cached = _template_cache.get(cache_key)
        if cached:
            rendered = str(cached)
        else:
            staff_map = _get_staff_map(trip_id, trip, store)
            rendered = _render_content(template_content, trip, staff_map)
            _template_cache.set(cache_key, rendered)
    else:
        staff_map = _get_staff_map(trip_id, trip, store)
        rendered = _render_content(template_content, trip, staff_map)

    now_str = datetime.now(tz=ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")
    rendered = f"【{now_str}】\n{rendered}"

    if preview:
        return True, rendered

    webhook = WeChatWorkWebhookProvider()
    return webhook.send(f"workflow:{template_key}:{trip.get('id','')}", rendered)


def _get_staff_map(trip_id: str, trip: dict, store) -> dict[str, str]:
    """获取人员映射（带缓存）。"""
    cache_key = f"staff:{trip_id}"
    cached = _staff_cache.get(cache_key)
    if cached:
        return dict(cached)
    staff_repo = TripStaffRepository(store=store)
    staff_map: dict[str, str] = {}
    for s in staff_repo.get_by_trip(trip_id):
        staff_map[s["role"]] = s.get("name", "")
        staff_map[f"{s['role']}_phone"] = s.get("phone", "")
    _staff_cache.set(cache_key, staff_map)
    return staff_map


def _render_content(template: str, trip: dict, staff_map: dict[str, str]) -> str:
    """渲染模板变量（减少重复计算）。"""
    vars_ = {
        "manager_name": staff_map.get("manager") or str(trip.get("trip_manager_name") or trip.get("concierge_name") or "负责人"),
        "manager_phone": staff_map.get("manager_phone") or str(trip.get("trip_manager_phone") or trip.get("contact_phone") or ""),
        "concierge_name": staff_map.get("concierge") or str(trip.get("concierge_name") or "管家"),
        "concierge_phone": staff_map.get("concierge_phone") or str(trip.get("concierge_phone") or trip.get("contact_phone") or ""),
        "driver_name": staff_map.get("driver") or str(trip.get("driver_name") or "司机"),
        "driver_phone": staff_map.get("driver_phone") or str(trip.get("driver_phone") or ""),
        "customer_name": str(trip.get("destination") or "贵宾"),
        "destination": str(trip.get("destination") or ""),
        "departure_date": str(trip.get("start_date") or ""),
    }
    rendered = template
    for k, v in vars_.items():
        rendered = rendered.replace("{{" + k + "}}", v)
    return rendered


def _check_idempotency(trip: dict[str, Any], action: str, *, store) -> bool:
    today = datetime.now(tz=ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
    repo = _get_wf_repo(store)
    for r in repo.get_by_trip(str(trip.get("id", ""))):
        if r.get("step_key") == action and r.get("completed"):
            if str(r.get("completed_at", "")).startswith(today):
                return True
    return False


def _mark_step(trip: dict[str, Any], step: str, *, store, operator_id: str = "", detail: dict | None = None) -> None:
    _get_wf_repo(store).mark(str(trip.get("id", "")), step, operator_id=operator_id, detail=detail or {})


# ── 行程前 ──────────────────────────────────────────────────────────────

async def send_pre_flight_notice(
    trip_id: str, user: dict, ctx, preview: bool = False,
) -> dict[str, Any]:
    from app.api.http import _require_permission_or_403, assert_trip_access, _ok
    _require_permission_or_403(user, "notification:write")
    trip = ctx.trip_repository.get(trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    assert_trip_access(user, trip)
    ok, msg = _send_template(trip, "pre_flight_notice", store=ctx.store, preview=preview)
    if preview:
        return _ok({"trip_id": trip_id, "preview": True, "rendered_content": msg})
    ctx.audit_service.record(operator_id=user["id"], action="pre_flight_notice_sent", target=trip_id, detail={"ok": ok})
    _mark_step(trip, "pre_flight_notice", store=ctx.store, operator_id=user["id"])
    if not ok:
        raise HTTPException(status_code=502, detail=f"WeChat push failed: {msg}")
    return _ok({"trip_id": trip_id, "message": "行前提示已发送"})


async def verify_resources(
    trip_id: str, body: ResourceVerifyRequest | None, user: dict, ctx,
) -> dict[str, Any]:
    from app.api.http import _require_permission_or_403, assert_trip_access, _ok
    _require_permission_or_403(user, "notification:write")
    trip = ctx.trip_repository.get(trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    assert_trip_access(user, trip)
    if _check_idempotency(trip, "resources_verified", store=ctx.store):
        return _ok({"trip_id": trip_id, "message": "资源核验已完成（今日已执行）", "idempotent": True})
    detail = {"hotel_ok": body.hotel_ok if body else True, "vehicle_ok": body.vehicle_ok if body else True, "equipment_ok": body.equipment_ok if body else True, "note": body.note if body else ""}
    _mark_step(trip, "resources_verified", store=ctx.store, operator_id=user["id"], detail=detail)
    ctx.audit_service.record(operator_id=user["id"], action="resources_verified", target=trip_id, detail=detail)
    return _ok({"trip_id": trip_id, "message": "资源核验已完成", "detail": detail})


async def verify_insurance(
    trip_id: str, body: InsuranceVerifyRequest | None, user: dict, ctx,
) -> dict[str, Any]:
    from app.api.http import _require_permission_or_403, assert_trip_access, _ok
    _require_permission_or_403(user, "notification:write")
    trip = ctx.trip_repository.get(trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    assert_trip_access(user, trip)
    if _check_idempotency(trip, "insurance_verified", store=ctx.store):
        return _ok({"trip_id": trip_id, "message": "保险核查已完成（今日已执行）", "idempotent": True})
    detail = {"insurance_ok": body.insurance_ok if body else True, "note": body.note if body else ""}
    _mark_step(trip, "insurance_verified", store=ctx.store, operator_id=user["id"], detail=detail)
    ctx.audit_service.record(operator_id=user["id"], action="insurance_verified", target=trip_id, detail=detail)
    return _ok({"trip_id": trip_id, "message": "保险核查已完成", "detail": detail})


async def build_group(
    trip_id: str, body: BuildGroupRequest | None, user: dict, ctx,
) -> dict[str, Any]:
    from app.api.http import _require_permission_or_403, assert_trip_access, _ok
    _require_permission_or_403(user, "notification:write")
    trip = ctx.trip_repository.get(trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    assert_trip_access(user, trip)
    if _check_idempotency(trip, "group_built", store=ctx.store):
        return _ok({"trip_id": trip_id, "message": "建群已完成（今日已执行）", "idempotent": True})

    steps = (body.steps if body else None) or ["driver_brief", "group_welcome", "pre_flight_notice"]
    results: list[dict[str, Any]] = []

    if "driver_brief" in steps:
        driver_name = str(trip.get("driver_name") or "司机")
        destination = str(trip.get("destination") or "")
        start_date = str(trip.get("start_date") or "")
        end_date = str(trip.get("end_date") or "")
        guests = trip.get("guests") or []
        itinerary = trip.get("itinerary") or []
        itinerary_text = "\n".join(f"  Day{i+1}: {day.get('title','') or day.get('location','') or ''}" for i, day in enumerate(itinerary[:7])) or "  请参见行程详情"
        now_str = datetime.now(tz=ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")
        driver_content = (
            f"【{now_str}】\n【行程确认单】{driver_name}师傅您好！\n"
            f"目的地：{destination}\n行程日期：{start_date} ~ {end_date}\n"
            f"游客人数：{len(guests)} 人\n行程简介：\n{itinerary_text}\n"
            f"负责人：{str(trip.get('trip_manager_name') or trip.get('concierge_name') or '管家')}"
            f"（{str(trip.get('contact_phone') or '')}）\n请提前检查车辆，准时就位，谢谢！"
        )
        webhook = WeChatWorkWebhookProvider()
        driver_ok, driver_msg = webhook.send(f"driver:{trip_id}", driver_content)
        results.append({"step": "driver_brief", "ok": driver_ok, "detail": driver_msg})

    if "group_welcome" in steps:
        w_ok, w_msg = _send_template(trip, "group_welcome", store=ctx.store)
        results.append({"step": "group_welcome", "ok": w_ok, "detail": w_msg})

    if "pre_flight_notice" in steps:
        p_ok, p_msg = _send_template(trip, "pre_flight_notice", store=ctx.store)
        results.append({"step": "pre_flight_notice", "ok": p_ok, "detail": p_msg})

    all_ok = all(r["ok"] for r in results)
    executed = [r["step"] for r in results]
    _mark_step(trip, "group_built", store=ctx.store, operator_id=user["id"], detail={"results": results, "steps": executed})
    ctx.audit_service.record(operator_id=user["id"], action="group_built", target=trip_id, detail={"results": results, "steps": executed})
    if not all_ok:
        raise HTTPException(status_code=502, detail=f"部分推送失败: {results}")
    return _ok({"trip_id": trip_id, "message": f"建群完成：已执行 {', '.join(executed)}", "results": results, "steps": executed})


# ── 行程中 ──────────────────────────────────────────────────────────────

async def send_day1_guide(
    trip_id: str, user: dict, ctx, preview: bool = False,
) -> dict[str, Any]:
    from app.api.http import _require_permission_or_403, assert_trip_access, _ok
    _require_permission_or_403(user, "notification:write")
    trip = ctx.trip_repository.get(trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    assert_trip_access(user, trip)
    if not preview and _check_idempotency(trip, "day1_guide_sent", store=ctx.store):
        return _ok({"trip_id": trip_id, "message": "落地首日指引已发送（今日已执行）", "idempotent": True})
    results: list[dict[str, Any]] = []
    u_ok, u_msg = _send_template(trip, "urumqi_day1_recommendations", store=ctx.store, preview=preview)
    results.append({"step": "urumqi_day1", "ok": u_ok, "detail": u_msg})
    t_ok, t_msg = _send_template(trip, "xinjiang_general_tips", store=ctx.store, preview=preview)
    results.append({"step": "xinjiang_tips", "ok": t_ok, "detail": t_msg})
    if preview:
        return _ok({"trip_id": trip_id, "preview": True, "results": results})
    all_ok = all(r["ok"] for r in results)
    _mark_step(trip, "day1_guide_sent", store=ctx.store, operator_id=user["id"])
    ctx.audit_service.record(operator_id=user["id"], action="day1_guide_sent", target=trip_id, detail={"results": results})
    if not all_ok:
        raise HTTPException(status_code=502, detail=f"部分推送失败: {results}")
    return _ok({"trip_id": trip_id, "message": "落地首日指引已发送", "results": results})


# ── 行程后 ──────────────────────────────────────────────────────────────

async def send_farewell(
    trip_id: str, user: dict, ctx, preview: bool = False,
) -> dict[str, Any]:
    from app.api.http import _require_permission_or_403, assert_trip_access, _ok
    _require_permission_or_403(user, "notification:write")
    trip = ctx.trip_repository.get(trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    assert_trip_access(user, trip)
    if not preview and _check_idempotency(trip, "farewell_sent", store=ctx.store):
        return _ok({"trip_id": trip_id, "message": "欢送词已发送（今日已执行）", "idempotent": True})
    ok, msg = _send_template(trip, "farewell_message", store=ctx.store, preview=preview)
    if preview:
        return _ok({"trip_id": trip_id, "preview": True, "rendered_content": msg})
    ctx.audit_service.record(operator_id=user["id"], action="farewell_sent", target=trip_id, detail={"ok": ok})
    _mark_step(trip, "farewell_sent", store=ctx.store, operator_id=user["id"])
    if not ok:
        raise HTTPException(status_code=502, detail=f"WeChat push failed: {msg}")
    return _ok({"trip_id": trip_id, "message": "欢送词已发送"})


async def send_survey(
    trip_id: str, user: dict, ctx, preview: bool = False,
) -> dict[str, Any]:
    from app.api.http import _require_permission_or_403, assert_trip_access, _ok
    _require_permission_or_403(user, "notification:write")
    trip = ctx.trip_repository.get(trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    assert_trip_access(user, trip)
    if not preview and _check_idempotency(trip, "survey_sent", store=ctx.store):
        return _ok({"trip_id": trip_id, "message": "满意度调研已发送（今日已执行）", "idempotent": True})
    ok, msg = _send_template(trip, "post_trip_survey_notice", store=ctx.store, preview=preview)
    if preview:
        return _ok({"trip_id": trip_id, "preview": True, "rendered_content": msg})
    ctx.audit_service.record(operator_id=user["id"], action="survey_sent", target=trip_id, detail={"ok": ok})
    _mark_step(trip, "survey_sent", store=ctx.store, operator_id=user["id"])
    if not ok:
        raise HTTPException(status_code=502, detail=f"WeChat push failed: {msg}")
    return _ok({"trip_id": trip_id, "message": "满意度调研已发送"})


async def dismiss_group(
    trip_id: str, user: dict, ctx, preview: bool = False,
) -> dict[str, Any]:
    from app.api.http import _require_permission_or_403, assert_trip_access, _ok
    _require_permission_or_403(user, "notification:write")
    trip = ctx.trip_repository.get(trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    assert_trip_access(user, trip)
    if not preview and _check_idempotency(trip, "group_dismissed", store=ctx.store):
        return _ok({"trip_id": trip_id, "message": "群解散通知已发送（今日已执行）", "idempotent": True})
    ok, msg = _send_template(trip, "group_close_message", store=ctx.store, preview=preview)
    if preview:
        return _ok({"trip_id": trip_id, "preview": True, "rendered_content": msg})
    ctx.audit_service.record(operator_id=user["id"], action="group_dismissed", target=trip_id, detail={"ok": ok})
    _mark_step(trip, "group_dismissed", store=ctx.store, operator_id=user["id"])
    if not ok:
        raise HTTPException(status_code=502, detail=f"WeChat push failed: {msg}")
    return _ok({"trip_id": trip_id, "message": "群解散通知已发送"})


# ── 状态 & 触发 ─────────────────────────────────────────────────────────

async def get_workflow_status(trip_id: str, user: dict, ctx) -> dict[str, Any]:
    from app.api.http import _require_permission_or_403, assert_trip_access, _ok
    _require_permission_or_403(user, "trip:read")
    # 读取缓存（5秒TTL）
    cache_key = f"wf_status:{trip_id}"
    cached = _workflow_cache.get(cache_key)
    if cached:
        return cached
    trip = ctx.trip_repository.get(trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    assert_trip_access(user, trip)

    wf_repo = _get_wf_repo(ctx.store)
    status_map = wf_repo.get_status_map(trip_id)

    playbook_repo = LifecyclePlaybookRepository(store=ctx.store)
    playbook = playbook_repo.list_all() or [
        {"stage": "pre_trip", "time_node": "出发前3天", "core_work": "游客沟通+行程单处理", "sort_order": 10},
        {"stage": "pre_trip", "time_node": "出发前", "core_work": "资源&物资确认", "sort_order": 20},
        {"stage": "pre_trip", "time_node": "出发前1天", "core_work": "保险核查+群聊搭建+司导交底", "sort_order": 30},
        {"stage": "in_trip", "time_node": "落地当日", "core_work": "本地指引+通用提示", "sort_order": 40},
        {"stage": "in_trip", "time_node": "每日固定时段", "core_work": "时段性温馨提示", "sort_order": 50},
        {"stage": "in_trip", "time_node": "特殊游玩场景", "core_work": "专项安全提示", "sort_order": 60},
        {"stage": "in_trip", "time_node": "全程", "core_work": "三方协调沟通", "sort_order": 70},
        {"stage": "post_trip", "time_node": "下团即时", "core_work": "欢送+满意度调研", "sort_order": 80},
        {"stage": "post_trip", "time_node": "下团后短期内", "core_work": "售后跟进+客户存档", "sort_order": 90},
        {"stage": "post_trip", "time_node": "售后末期", "core_work": "群聊解散", "sort_order": 100},
    ]

    step_key_map = {
        "游客沟通+行程单处理": "pre_flight_notice",
        "资源&物资确认": "resources_verified",
        "保险核查+群聊搭建+司导交底": "group_built",
        "本地指引+通用提示": "day1_guide_sent",
        "欢送+满意度调研": "farewell_sent",
        "群聊解散": "group_dismissed",
    }

    start_date = str(trip.get("start_date") or "")
    end_date = str(trip.get("end_date") or "")
    today = datetime.now(tz=ZoneInfo("Asia/Shanghai")).date()
    current_stage = "unknown"
    if start_date:
        ts = datetime.strptime(start_date, "%Y-%m-%d").date()
        if (ts - today).days > 1: current_stage = "pre_trip"
        elif (ts - today).days >= 0: current_stage = "in_trip"
    if end_date and current_stage != "pre_trip":
        te = datetime.strptime(end_date, "%Y-%m-%d").date()
        if (today - te).days >= 0: current_stage = "post_trip"

    steps_by_stage: dict = {"pre_trip": [], "in_trip": [], "post_trip": []}
    for item in playbook:
        stage = item.get("stage", "")
        if stage not in steps_by_stage: continue
        sk = step_key_map.get(item.get("core_work", ""), item.get("core_work", "").replace(" ", "_"))
        st = status_map.get(sk)
        steps_by_stage[stage].append({
            "key": sk, "label": item.get("core_work", ""), "time_node": item.get("time_node", ""),
            "completed": bool(st.get("completed")) if st else False,
            "completed_at": st.get("completed_at") if st else None,
        })

    all_steps = steps_by_stage["pre_trip"] + steps_by_stage["in_trip"] + steps_by_stage["post_trip"]
    result = _ok({
        "trip_id": trip_id, "current_stage": current_stage,
        "start_date": start_date, "end_date": end_date,
        "progress": {"completed": sum(1 for s in all_steps if s["completed"]), "total": len(all_steps)},
        "pre_trip": steps_by_stage["pre_trip"], "in_trip": steps_by_stage["in_trip"], "post_trip": steps_by_stage["post_trip"],
    })
    _workflow_cache.set(cache_key, result)
    return result


async def trigger_scheduler(trip_id: str, body: TriggerSchedulerRequest | None, user: dict, ctx) -> dict[str, Any]:
    from app.api.http import _require_permission_or_403, assert_trip_access, _ok
    _require_permission_or_403(user, "notification:write")
    trip = ctx.trip_repository.get(trip_id)
    if trip is None: raise HTTPException(status_code=404, detail="Trip not found")
    assert_trip_access(user, trip)
    slot = (body.time_slot if body else "morning") or "morning"
    if hasattr(ctx, "scheduler_service") and ctx.scheduler_service is not None:
        import asyncio
        asyncio.ensure_future(ctx.scheduler_service.check_and_send_notifications_for_slot(slot))
    ctx.audit_service.record(operator_id=user["id"], action="scheduler_triggered", target=trip_id, detail={"time_slot": slot})
    return _ok({"trip_id": trip_id, "message": f"已触发 {slot} 时段调度检查"})


async def batch_send_workflow(body: BatchSendWorkflowRequest, user: dict, ctx) -> dict[str, Any]:
    from app.api.http import _require_permission_or_403, assert_trip_access, _ok
    _require_permission_or_403(user, "notification:write")
    results: list[dict[str, Any]] = []
    for tid in body.trip_ids:
        trip = ctx.trip_repository.get(tid)
        if trip is None:
            results.append({"trip_id": tid, "ok": False, "error": "Trip not found"})
            continue
        try:
            assert_trip_access(user, trip)
            ok, msg = _send_template(trip, body.template_key, store=ctx.store)
            results.append({"trip_id": tid, "ok": ok, "detail": msg})
        except HTTPException as e:
            results.append({"trip_id": tid, "ok": False, "error": str(e.detail)})
    success = [r for r in results if r.get("ok")]
    ctx.audit_service.record(operator_id=user["id"], action="batch_workflow_sent", target="", detail={"template": body.template_key, "total": len(body.trip_ids), "ok": len(success)})
    return _ok({"template_key": body.template_key, "results": results, "success_count": len(success), "total": len(body.trip_ids)})
