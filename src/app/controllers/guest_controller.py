"""游客控制器 — HTTP 请求/响应处理."""

from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException

from app.dao.repositories import GuestRepository, TripGuestRepository
from app.models.dto.requests import GuestCreateRequest, GuestUpdateRequest


async def list_trip_guests(trip_id: str, user: dict, ctx) -> dict[str, Any]:
    from app.api.http import _require_permission_or_403, assert_trip_access, _ok
    _require_permission_or_403(user, "trip:read")
    trip = ctx.trip_repository.get(trip_id)
    if trip is None: raise HTTPException(status_code=404, detail="Trip not found")
    assert_trip_access(user, trip)
    guest_repo = GuestRepository(store=ctx.store)
    tg_repo = TripGuestRepository(store=ctx.store)
    guest_ids = tg_repo.get_guest_ids(trip_id)
    guests = [g for gid in guest_ids if (g := guest_repo.get(gid))]
    if not guests:
        guests = trip.get("guests") or []
    return _ok({"trip_id": trip_id, "guests": guests, "total": len(guests)})


async def add_trip_guest(trip_id: str, body: GuestCreateRequest, user: dict, ctx) -> dict[str, Any]:
    from app.api.http import _require_permission_or_403, assert_trip_access, _ok
    _require_permission_or_403(user, "trip:write")
    trip = ctx.trip_repository.get(trip_id)
    if trip is None: raise HTTPException(status_code=404, detail="Trip not found")
    assert_trip_access(user, trip)
    guest_repo = GuestRepository(store=ctx.store)
    tg_repo = TripGuestRepository(store=ctx.store)
    guest = guest_repo.get_by_phone(body.phone) or guest_repo.create({"name": body.name, "phone": body.phone})
    tg_repo.link(trip_id, str(guest["id"]))
    ctx.audit_service.record(operator_id=user["id"], action="guest_added", target=trip_id, detail={"guest_id": guest["id"], "name": body.name})
    return _ok({"trip_id": trip_id, "guest": guest, "message": "游客已添加"})


async def update_guest_phone(trip_id: str, guest_id: str, body: GuestUpdateRequest, user: dict, ctx) -> dict[str, Any]:
    from app.api.http import _require_permission_or_403, assert_trip_access, _ok
    _require_permission_or_403(user, "trip:write")
    trip = ctx.trip_repository.get(trip_id)
    if trip is None: raise HTTPException(status_code=404, detail="Trip not found")
    assert_trip_access(user, trip)
    repo = GuestRepository(store=ctx.store)
    patch = {k: v for k, v in {"name": body.name, "phone": body.phone}.items() if v is not None}
    updated = repo.update(guest_id, patch)
    if updated is None: raise HTTPException(status_code=404, detail="Guest not found")
    return _ok({"trip_id": trip_id, "guest": updated, "message": "游客信息已更新"})


async def remove_trip_guest(trip_id: str, guest_id: str, user: dict, ctx) -> dict[str, Any]:
    from app.api.http import _require_permission_or_403, assert_trip_access, _ok
    _require_permission_or_403(user, "trip:write")
    trip = ctx.trip_repository.get(trip_id)
    if trip is None: raise HTTPException(status_code=404, detail="Trip not found")
    assert_trip_access(user, trip)
    tg_repo = TripGuestRepository(store=ctx.store)
    ok = tg_repo.unlink(trip_id, guest_id)
    ctx.audit_service.record(operator_id=user["id"], action="guest_removed", target=trip_id, detail={"guest_id": guest_id})
    return _ok({"trip_id": trip_id, "guest_id": guest_id, "removed": ok})


async def list_guests(is_vip: bool | None, search: str | None, user: dict, ctx) -> dict[str, Any]:
    from app.api.http import _require_permission_or_403, _ok
    _require_permission_or_403(user, "trip:read")
    repo = GuestRepository(store=ctx.store)
    guests = repo.list()
    if is_vip is not None:
        guests = [g for g in guests if bool(g.get("is_vip")) == is_vip]
    if search:
        s = search.lower()
        guests = [g for g in guests if s in str(g.get("name", "")).lower() or s in str(g.get("phone", ""))]
    return _ok({"guests": guests, "total": len(guests)})


async def update_guest(guest_id: str, body: GuestUpdateRequest, user: dict, ctx) -> dict[str, Any]:
    from app.api.http import _require_permission_or_403, _ok
    _require_permission_or_403(user, "trip:write")
    repo = GuestRepository(store=ctx.store)
    patch = {k: v for k, v in {"name": body.name, "phone": body.phone}.items() if v is not None}
    if not patch: raise HTTPException(status_code=400, detail="No fields to update")
    updated = repo.update(guest_id, patch)
    if updated is None: raise HTTPException(status_code=404, detail="Guest not found")
    ctx.audit_service.record(operator_id=user["id"], action="guest_updated", target=guest_id, detail=patch)
    return _ok({"guest": updated, "message": "游客信息已更新"})


async def delete_guest(guest_id: str, user: dict, ctx) -> dict[str, Any]:
    from app.api.http import _require_permission_or_403, _ok
    _require_permission_or_403(user, "trip:write")
    guest_repo = GuestRepository(store=ctx.store)
    tg_repo = TripGuestRepository(store=ctx.store)
    linked = tg_repo.get_trip_ids(guest_id)
    for tid in linked: tg_repo.unlink(tid, guest_id)
    ok = guest_repo.delete(guest_id)
    ctx.audit_service.record(operator_id=user["id"], action="guest_deleted", target=guest_id, detail={"unlinked": len(linked)})
    return _ok({"guest_id": guest_id, "deleted": ok, "unlinked_trips": len(linked)})
