"""游客路由层 — URL → Controller 映射."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.controllers.guest_controller import (
    list_trip_guests,
    add_trip_guest,
    update_guest_phone,
    remove_trip_guest,
    list_guests,
    update_guest,
    delete_guest,
)
from app.models.dto.requests import GuestCreateRequest, GuestUpdateRequest

router = APIRouter(prefix="/api", tags=["guests"])


@router.get("/trips/{trip_id}/guests")
async def trip_guests(trip_id: str, user: dict[str, str] = Depends(), ctx = Depends()) -> dict[str, Any]:
    return await list_trip_guests(trip_id, user, ctx)


@router.post("/trips/{trip_id}/guests", status_code=201)
async def add_guest(trip_id: str, body: GuestCreateRequest, user: dict[str, str] = Depends(), ctx = Depends()) -> dict[str, Any]:
    return await add_trip_guest(trip_id, body, user, ctx)


@router.put("/trips/{trip_id}/guests/{guest_id}/phone")
async def update_phone(trip_id: str, guest_id: str, body: GuestUpdateRequest, user: dict[str, str] = Depends(), ctx = Depends()) -> dict[str, Any]:
    return await update_guest_phone(trip_id, guest_id, body, user, ctx)


@router.delete("/trips/{trip_id}/guests/{guest_id}")
async def remove_guest(trip_id: str, guest_id: str, user: dict[str, str] = Depends(), ctx = Depends()) -> dict[str, Any]:
    return await remove_trip_guest(trip_id, guest_id, user, ctx)


@router.get("/guests")
async def all_guests(is_vip: bool | None = None, search: str | None = None, user: dict[str, str] = Depends(), ctx = Depends()) -> dict[str, Any]:
    return await list_guests(is_vip, search, user, ctx)


@router.put("/guests/{guest_id}")
async def update_a_guest(guest_id: str, body: GuestUpdateRequest, user: dict[str, str] = Depends(), ctx = Depends()) -> dict[str, Any]:
    return await update_guest(guest_id, body, user, ctx)


@router.delete("/guests/{guest_id}")
async def delete_a_guest(guest_id: str, user: dict[str, str] = Depends(), ctx = Depends()) -> dict[str, Any]:
    return await delete_guest(guest_id, user, ctx)
