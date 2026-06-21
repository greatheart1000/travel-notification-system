"""工作流路由层 — URL → Controller 映射."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.controllers.workflow_controller import (
    send_pre_flight_notice as ctrl_send_pre_flight,
    verify_resources as ctrl_verify_resources,
    verify_insurance as ctrl_verify_insurance,
    build_group as ctrl_build_group,
    send_day1_guide as ctrl_send_day1_guide,
    send_farewell as ctrl_send_farewell,
    send_survey as ctrl_send_survey,
    dismiss_group as ctrl_dismiss_group,
    get_workflow_status as ctrl_get_workflow_status,
    trigger_scheduler as ctrl_trigger_scheduler,
    batch_send_workflow as ctrl_batch_send_workflow,
)
from app.models.dto.requests import (
    ResourceVerifyRequest,
    InsuranceVerifyRequest,
    BuildGroupRequest,
    TriggerSchedulerRequest,
    BatchSendWorkflowRequest,
)

router = APIRouter(prefix="/api", tags=["workflow"])


# ── 行程前 ──────────────────────────────────────────────────────────────

@router.post("/trips/{trip_id}/pre-trip/send-pre-flight-notice")
async def send_pre_flight_notice(
    trip_id: str,
    preview: bool = False,
    user: dict[str, str] = Depends(),
    ctx = Depends(),
) -> dict[str, Any]:
    return await ctrl_send_pre_flight(trip_id, user, ctx, preview=preview)


@router.post("/trips/{trip_id}/pre-trip/verify-resources")
async def verify_resources(
    trip_id: str,
    body: ResourceVerifyRequest | None = None,
    user: dict[str, str] = Depends(),
    ctx = Depends(),
) -> dict[str, Any]:
    return await ctrl_verify_resources(trip_id, body, user, ctx)


@router.post("/trips/{trip_id}/pre-trip/verify-insurance")
async def verify_insurance(
    trip_id: str,
    body: InsuranceVerifyRequest | None = None,
    user: dict[str, str] = Depends(),
    ctx = Depends(),
) -> dict[str, Any]:
    return await ctrl_verify_insurance(trip_id, body, user, ctx)


@router.post("/trips/{trip_id}/pre-trip/build-group")
async def build_group(
    trip_id: str,
    body: BuildGroupRequest | None = None,
    user: dict[str, str] = Depends(),
    ctx = Depends(),
) -> dict[str, Any]:
    return await ctrl_build_group(trip_id, body, user, ctx)


# ── 行程中 ──────────────────────────────────────────────────────────────

@router.post("/trips/{trip_id}/in-trip/send-day1-guide")
async def send_day1_guide(
    trip_id: str,
    preview: bool = False,
    user: dict[str, str] = Depends(),
    ctx = Depends(),
) -> dict[str, Any]:
    return await ctrl_send_day1_guide(trip_id, user, ctx, preview=preview)


# ── 行程后 ──────────────────────────────────────────────────────────────

@router.post("/trips/{trip_id}/post-trip/send-farewell")
async def send_farewell(
    trip_id: str,
    preview: bool = False,
    user: dict[str, str] = Depends(),
    ctx = Depends(),
) -> dict[str, Any]:
    return await ctrl_send_farewell(trip_id, user, ctx, preview=preview)


@router.post("/trips/{trip_id}/post-trip/send-survey")
async def send_survey(
    trip_id: str,
    preview: bool = False,
    user: dict[str, str] = Depends(),
    ctx = Depends(),
) -> dict[str, Any]:
    return await ctrl_send_survey(trip_id, user, ctx, preview=preview)


@router.post("/trips/{trip_id}/post-trip/dismiss-group")
async def dismiss_group(
    trip_id: str,
    preview: bool = False,
    user: dict[str, str] = Depends(),
    ctx = Depends(),
) -> dict[str, Any]:
    return await ctrl_dismiss_group(trip_id, user, ctx, preview=preview)


# ── 状态 & 触发 ─────────────────────────────────────────────────────────

@router.get("/trips/{trip_id}/workflow-status")
async def workflow_status(
    trip_id: str,
    user: dict[str, str] = Depends(),
    ctx = Depends(),
) -> dict[str, Any]:
    return await ctrl_get_workflow_status(trip_id, user, ctx)


@router.post("/trips/{trip_id}/trigger-scheduler")
async def trigger_scheduler(
    trip_id: str,
    body: TriggerSchedulerRequest | None = None,
    user: dict[str, str] = Depends(),
    ctx = Depends(),
) -> dict[str, Any]:
    return await ctrl_trigger_scheduler(trip_id, body, user, ctx)


@router.post("/trips/batch/send-workflow")
async def batch_send_workflow(
    body: BatchSendWorkflowRequest,
    user: dict[str, str] = Depends(),
    ctx = Depends(),
) -> dict[str, Any]:
    return await ctrl_batch_send_workflow(body, user, ctx)
