from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator
from starlette.routing import Router as StarletteRouter

from app.core.entities import Channel as PreferenceChannel
from app.core.models import Channel
from app.modules.audit.service import AuditLogRepository, AuditService
from app.modules.integration.auth import AuthService
from app.modules.integration.persistence import JsonFileStore, TripRepository
from app.modules.notification.models import NotificationTask
from app.modules.notification.service import NotificationAttemptRepository, NotificationService
from app.services.preference_service import UserPreferenceService
from app.services.template_service import TemplateService

UTC = UTC


def _patch_starlette_router_compat() -> None:
    """
    Compatibility shim for environments where FastAPI and Starlette versions
    are temporarily misaligned (FastAPI passes on_startup/on_shutdown).
    """

    if getattr(StarletteRouter.__init__, "_fastapi_compat_patched", False):
        return

    original_init = StarletteRouter.__init__

    def _patched_init(self: StarletteRouter, *args: Any, **kwargs: Any) -> None:
        kwargs.pop("on_startup", None)
        kwargs.pop("on_shutdown", None)
        original_init(self, *args, **kwargs)

    _patched_init._fastapi_compat_patched = True  # type: ignore[attr-defined]
    StarletteRouter.__init__ = _patched_init  # type: ignore[assignment]


@dataclass(slots=True)
class Response:
    status: int
    body: dict[str, Any]


@dataclass(slots=True)
class AppContext:
    store: JsonFileStore
    auth_service: AuthService
    trip_repository: TripRepository
    template_service: TemplateService
    preference_service: UserPreferenceService
    notification_attempt_repository: NotificationAttemptRepository
    notification_service: NotificationService
    audit_service: AuditService


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class PreferenceUpdateRequest(BaseModel):
    channels: list[str] = Field(default_factory=list)
    quiet_hours: list[int] | dict[str, Any] = Field(default_factory=lambda: [23, 7])
    max_notifications_per_hour: int | None = None
    auto_escalation: bool | None = None
    aggregate_notifications: bool | None = None
    allow_marketing: bool | None = None


class TemplateCreateRequest(BaseModel):
    name: str
    content: str
    channel: str = "sms"
    notification_type: str = "daily_reminder"
    is_active: bool = True


class TemplateUpdateRequest(BaseModel):
    name: str | None = None
    content: str | None = None
    channel: str | None = None
    notification_type: str | None = None
    is_active: bool | None = None


class TripCreateRequest(BaseModel):
    destination: str
    team: str | None = None
    team_id: str | None = None
    start_date: str
    end_date: str
    participants: int = 0
    status: str = "计划中"


class TripUpdateRequest(BaseModel):
    destination: str | None = None
    team: str | None = None
    team_id: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    participants: int | None = None
    status: str | None = None

    @field_validator("team", "team_id")
    @classmethod
    def validate_team_fields(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return value.strip()


class NotificationSendRequest(BaseModel):
    template_id: str | None = None
    trip_id: str | None = None
    trip: str | None = None
    team: str | None = None
    team_id: str | None = None
    customer_name: str | None = None
    destination: str | None = None
    channel: str = "sms"


def _ok(data: Any) -> dict[str, Any]:
    return {"code": 200, "data": data}


def _error(status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"code": status, "error": message})


def _parse_channel(value: str) -> Channel:
    raw = value.strip().lower()
    if raw in {"短信"}:
        raw = "sms"
    if raw in {"企业微信", "wechat", "wechat_work"}:
        raw = "wechat_work_group"
    matched = next((item for item in Channel if item.value == raw), None)
    return matched or Channel.SMS


def _normalize_trip_status(value: str) -> str:
    mapping = {
        "计划中": "planned",
        "planned": "planned",
        "进行中": "in_progress",
        "active": "in_progress",
        "in_progress": "in_progress",
        "已完成": "completed",
        "completed": "completed",
        "已取消": "cancelled",
        "cancelled": "cancelled",
    }
    return mapping.get(value, value)


def _to_internal_preference_channel(value: str) -> str:
    raw = value.strip().lower()
    mapping = {
        "wechat_work_group": "push",
        "wechat": "push",
        "push": "push",
        "sms": "sms",
        "email": "email",
    }
    return mapping.get(raw, raw)


def _to_api_preference_channel(value: str) -> str:
    raw = value.strip().lower()
    if raw == "push":
        return "wechat_work_group"
    return raw


def _normalize_preference_payload(payload: dict[str, Any]) -> dict[str, Any]:
    channels = payload.get("channels", [])
    normalized_channels: list[str] = []
    if isinstance(channels, list):
        for item in channels:
            normalized = _to_api_preference_channel(str(item))
            if normalized not in {"sms", "wechat_work_group", "email"}:
                continue
            if normalized not in normalized_channels:
                normalized_channels.append(normalized)
    result = dict(payload)
    result["channels"] = normalized_channels
    return result


def _resolve_team_id(team: str | None, team_id: str | None) -> str:
    return (team_id or team or "").strip()


def _serialize_trip(trip: dict[str, Any]) -> dict[str, Any]:
    resolved_team_id = str(trip.get("team_id") or trip.get("team") or "")
    return {
        "id": trip.get("id", ""),
        "destination": trip.get("destination", ""),
        "team_id": resolved_team_id,
        "team": resolved_team_id,
        "start_date": trip.get("start_date", ""),
        "end_date": trip.get("end_date", ""),
        "participants": int(trip.get("participants", 0)),
        "status": _normalize_trip_status(str(trip.get("status", "planned"))),
        "user_id": trip.get("user_id", ""),
        "created_at": trip.get("created_at"),
        "updated_at": trip.get("updated_at"),
    }


def _normalize_history_item(item: dict[str, Any]) -> dict[str, Any]:
    ok = bool(item.get("ok", False))
    raw_status = str(item.get("status", "sent")).lower()
    status = raw_status
    if raw_status in {"", "pending"}:
        status = "sent" if ok else "failed"
    return {
        "id": item.get("attempt_id", ""),
        "attempt_id": item.get("attempt_id", ""),
        "task_id": item.get("task_id", ""),
        "trip_id": item.get("trip_id", ""),
        "team_id": item.get("team_id", ""),
        "customer_id": item.get("customer_id", ""),
        "attempt_no": int(item.get("attempt_no", 1)),
        "channel": str(item.get("channel", "sms")).lower(),
        "status": status,
        "ok": ok,
        "reason": item.get("reason", ""),
        "provider_message": item.get("provider_message", ""),
        "latency_ms": int(item.get("latency_ms", 0)),
        "attempted_at": item.get("attempted_at"),
    }


def _to_recent_item(item: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_history_item(item)
    return {
        "id": normalized["id"],
        "customer_name": normalized["customer_id"],
        "trip": normalized["trip_id"],
        "team_id": normalized["team_id"],
        "team": normalized["team_id"],
        "channel": normalized["channel"],
        "status": normalized["status"],
        "created_at": normalized["attempted_at"],
    }


def _query_notification_items(
    *,
    repository: NotificationAttemptRepository,
    limit: int,
    trip_id: str | None,
    team_id: str | None,
    customer_id: str | None,
    channel: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    raw_items = repository.list_history(
        limit=None,
        trip_id=trip_id,
        team_id=team_id,
        customer_id=customer_id,
    )
    normalized = [_normalize_history_item(item) for item in raw_items]
    if channel:
        normalized = [item for item in normalized if item["channel"] == channel.lower()]
    if status:
        normalized = [item for item in normalized if item["status"] == status.lower()]
    normalized_sorted = sorted(
        normalized,
        key=lambda item: (str(item.get("attempted_at") or ""), str(item.get("id") or "")),
        reverse=True,
    )
    return normalized_sorted[: max(limit, 0)]


def _serialize_template(template: Any) -> dict[str, Any]:
    status = "enabled" if template.is_active else "disabled"
    return {
        "id": template.id,
        "name": template.name,
        "version": template.version,
        "notification_type": template.notification_type.value,
        "channel": template.channel.value,
        "status": status,
        "enabled": template.is_active,
        "template": template.content,
        "content": template.content,
        "is_active": template.is_active,
        "created_at": template.created_at,
        "updated_at": template.updated_at,
    }


def _build_context(store: JsonFileStore | None = None) -> AppContext:
    persistence = store or JsonFileStore()
    trip_repository = TripRepository(store=persistence)
    template_service = TemplateService(store=persistence)
    template_service.ensure_default_template()
    preference_service = UserPreferenceService(store=persistence)
    notification_attempt_repository = NotificationAttemptRepository(store=persistence)
    notification_service = NotificationService(attempt_repository=notification_attempt_repository)
    audit_service = AuditService(repository=AuditLogRepository(store=persistence))
    auth_service = AuthService()
    return AppContext(
        store=persistence,
        auth_service=auth_service,
        trip_repository=trip_repository,
        template_service=template_service,
        preference_service=preference_service,
        notification_attempt_repository=notification_attempt_repository,
        notification_service=notification_service,
        audit_service=audit_service,
    )


def create_app() -> FastAPI:
    _patch_starlette_router_compat()
    fastapi_app = FastAPI(title="Travel Notification API", version="0.2.0")
    fastapi_app.state.ctx = _build_context()

    security = HTTPBearer(auto_error=False)

    def get_ctx(request: Request) -> AppContext:
        return request.app.state.ctx

    def get_current_user(
        credentials: HTTPAuthorizationCredentials | None = Depends(security),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, str]:
        if credentials is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = ctx.auth_service.authenticate(credentials.credentials)
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user

    def require_admin(user: dict[str, str] = Depends(get_current_user)) -> dict[str, str]:
        if user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin role required")
        return user

    def assert_trip_access(user: dict[str, str], trip: dict[str, Any]) -> None:
        if user.get("role") == "admin":
            return
        if trip.get("user_id") != user.get("id"):
            raise HTTPException(status_code=403, detail="Forbidden")

    @fastapi_app.exception_handler(HTTPException)
    async def _http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        return _error(exc.status_code, str(exc.detail))

    @fastapi_app.exception_handler(RequestValidationError)
    async def _validation_exception_handler(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"code": 422, "error": "Validation error", "detail": exc.errors()},
        )

    @fastapi_app.get("/api/health")
    def get_health() -> dict[str, Any]:
        return _ok({"status": "ok", "time": datetime.now(tz=UTC).isoformat(), "version": "0.2.0"})

    @fastapi_app.get("/api/health/detail")
    def get_health_detail(ctx: AppContext = Depends(get_ctx)) -> dict[str, Any]:
        attempts = ctx.notification_attempt_repository.list_history(limit=9999)
        return _ok(
            {
                "status": "ok",
                "time": datetime.now(tz=UTC).isoformat(),
                "components": {
                    "auth": {"status": "ok", "users": len(ctx.auth_service.users)},
                    "persistence": {"status": "ok", "base_dir": str(ctx.store.base_dir)},
                    "trip_repository": {"status": "ok", "count": len(ctx.trip_repository.list())},
                    "template_repository": {
                        "status": "ok",
                        "count": len(ctx.template_service.list_notification_templates()),
                    },
                    "notification_attempt_repository": {"status": "ok", "count": len(attempts)},
                    "audit_repository": {
                        "status": "ok",
                        "count": len(ctx.audit_service.repository.logs),
                    },
                },
            }
        )

    @fastapi_app.post("/api/auth/login")
    def login(payload: LoginRequest, ctx: AppContext = Depends(get_ctx)) -> dict[str, Any]:
        token = ctx.auth_service.login(payload.username, payload.password)
        if token is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return _ok(token)

    @fastapi_app.post("/api/auth/logout")
    def logout(
        credentials: HTTPAuthorizationCredentials | None = Depends(security),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        if credentials is not None:
            ctx.auth_service.logout(credentials.credentials)
        return {"code": 200}

    @fastapi_app.post("/api/auth/refresh")
    def refresh(payload: RefreshRequest, ctx: AppContext = Depends(get_ctx)) -> dict[str, Any]:
        token = ctx.auth_service.refresh(payload.refresh_token)
        if token is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        return _ok(token)

    @fastapi_app.get("/api/users/me")
    def me(user: dict[str, str] = Depends(get_current_user)) -> dict[str, Any]:
        return _ok(user)

    @fastapi_app.get("/api/preferences/me")
    def get_preferences_me(
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        payload = ctx.preference_service.get_preference_payload(user["id"])
        return _ok(_normalize_preference_payload(payload))

    @fastapi_app.put("/api/preferences/me")
    def update_preferences_me(
        payload: PreferenceUpdateRequest,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        if isinstance(payload.quiet_hours, list) and len(payload.quiet_hours) != 2:
            raise HTTPException(status_code=400, detail="quiet_hours must have 2 integers")
        if isinstance(payload.quiet_hours, dict):
            if "start" not in payload.quiet_hours or "end" not in payload.quiet_hours:
                raise HTTPException(
                    status_code=400, detail="quiet_hours object must contain start/end"
                )
        channels = payload.channels or [PreferenceChannel.EMAIL.value, PreferenceChannel.PUSH.value]
        internal_channels = [_to_internal_preference_channel(item) for item in channels]
        pref = ctx.preference_service.set_preference_from_payload(
            user_id=user["id"],
            channels=internal_channels,
            quiet_hours=payload.quiet_hours,
            max_notifications_per_hour=payload.max_notifications_per_hour,
            auto_escalation=payload.auto_escalation,
            aggregate_notifications=payload.aggregate_notifications,
            allow_marketing=payload.allow_marketing,
        )
        return _ok(_normalize_preference_payload(ctx.preference_service.to_payload(pref)))

    @fastapi_app.get("/api/preferences")
    def get_preferences(
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        return get_preferences_me(user=user, ctx=ctx)

    @fastapi_app.put("/api/preferences")
    def update_preferences(
        payload: PreferenceUpdateRequest,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        return update_preferences_me(payload=payload, user=user, ctx=ctx)

    @fastapi_app.get("/api/templates")
    def list_templates(
        _: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        items = [
            _serialize_template(item) for item in ctx.template_service.list_notification_templates()
        ]
        return _ok({"total": len(items), "items": items})

    @fastapi_app.get("/api/templates/{template_id}")
    def get_template(
        template_id: str,
        _: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        template = ctx.template_service.get_notification_template(template_id)
        if template is None:
            raise HTTPException(status_code=404, detail="Template not found")
        return _ok(_serialize_template(template))

    @fastapi_app.post("/api/templates", status_code=201)
    def create_template(
        payload: TemplateCreateRequest,
        _: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        template = ctx.template_service.create_notification_template(
            name=payload.name,
            content=payload.content,
            channel=_parse_channel(payload.channel).value,
            notification_type=payload.notification_type,
            is_active=payload.is_active,
        )
        return _ok(_serialize_template(template))

    @fastapi_app.put("/api/templates/{template_id}")
    def update_template(
        template_id: str,
        payload: TemplateUpdateRequest,
        _: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        template = ctx.template_service.update_notification_template(
            template_id,
            name=payload.name,
            content=payload.content,
            channel=None if payload.channel is None else _parse_channel(payload.channel).value,
            notification_type=payload.notification_type,
            is_active=payload.is_active,
        )
        if template is None:
            raise HTTPException(status_code=404, detail="Template not found")
        ctx.audit_service.record(
            operator_id="system", action="template_updated", target=template_id, detail={}
        )
        return _ok(_serialize_template(template))

    @fastapi_app.delete("/api/templates/{template_id}")
    def delete_template(
        template_id: str,
        _: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        deleted = ctx.template_service.delete_notification_template(template_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Template not found")
        ctx.audit_service.record(
            operator_id="system", action="template_deleted", target=template_id, detail={}
        )
        return {"code": 200}

    @fastapi_app.get("/api/notifications/templates")
    def list_templates_alias(
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        return list_templates(user, ctx)

    @fastapi_app.post("/api/notifications/templates", status_code=201)
    def create_templates_alias(
        payload: TemplateCreateRequest,
        user: dict[str, str] = Depends(require_admin),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        return create_template(payload, user, ctx)

    @fastapi_app.get("/api/trips")
    def list_trips(
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        items = ctx.trip_repository.list()
        if user.get("role") != "admin":
            items = [item for item in items if item.get("user_id") == user.get("id")]
        normalized_items = [_serialize_trip(item) for item in items]
        return _ok({"total": len(normalized_items), "items": normalized_items})

    @fastapi_app.post("/api/trips", status_code=201)
    def create_trip(
        payload: TripCreateRequest,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        team_id = _resolve_team_id(payload.team, payload.team_id)
        if not team_id:
            raise HTTPException(status_code=400, detail="Missing required field: team or team_id")
        trip_id = f"trip-{uuid4().hex[:8]}"
        now = datetime.now(tz=UTC).isoformat()
        trip = {
            "id": trip_id,
            "destination": payload.destination,
            "team": team_id,
            "team_id": team_id,
            "start_date": payload.start_date,
            "end_date": payload.end_date,
            "participants": payload.participants,
            "status": _normalize_trip_status(payload.status),
            "user_id": user["id"],
            "created_at": now,
            "updated_at": now,
        }
        ctx.trip_repository.create(trip)

        template = next(
            (item for item in ctx.template_service.list_notification_templates() if item.is_active),
            ctx.template_service.ensure_default_template(),
        )
        rendered = ctx.template_service.render_notification(
            template,
            {
                "customer_name": user.get("username", user["id"]),
                "destination": payload.destination,
            },
        )
        task = NotificationTask(
            team_id=team_id,
            trip_id=trip_id,
            customer_id=user["id"],
            rendered_content=rendered,
            idempotency_key=f"{trip_id}:created",
            primary_channel=Channel.SMS,
            fallback_channel=Channel.WECHAT_WORK_GROUP,
        )
        dispatch_result = ctx.notification_service.dispatch(task)
        ctx.audit_service.record(
            operator_id=user["id"],
            action="trip_created",
            target=trip_id,
            detail={"destination": payload.destination, "team_id": team_id},
        )
        ctx.audit_service.record(
            operator_id=user["id"],
            action="notification_dispatched",
            target=trip_id,
            detail={"ok": dispatch_result["ok"], "attempts": len(task.attempts)},
        )
        return _ok(
            {
                "trip": _serialize_trip(trip),
                "notification": {
                    "ok": dispatch_result["ok"],
                    "status": task.status.value,
                    "attempt_count": len(task.attempts),
                },
            }
        )

    @fastapi_app.put("/api/trips/{trip_id}")
    def update_trip(
        trip_id: str,
        payload: TripUpdateRequest,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        existing = ctx.trip_repository.get(trip_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Trip not found")
        assert_trip_access(user, existing)

        patch = payload.model_dump(exclude_none=True)
        if "team_id" in patch or "team" in patch:
            normalized_team_id = _resolve_team_id(
                patch.get("team") if isinstance(patch.get("team"), str) else None,
                patch.get("team_id") if isinstance(patch.get("team_id"), str) else None,
            )
            if not normalized_team_id:
                raise HTTPException(status_code=400, detail="team/team_id cannot be empty")
            patch["team_id"] = normalized_team_id
            patch["team"] = normalized_team_id
        if "status" in patch and isinstance(patch["status"], str):
            patch["status"] = _normalize_trip_status(patch["status"])
        updated = ctx.trip_repository.update(trip_id, patch)
        if updated is None:
            raise HTTPException(status_code=404, detail="Trip not found")
        ctx.audit_service.record(
            operator_id=user["id"], action="trip_updated", target=trip_id, detail=patch
        )
        return _ok(_serialize_trip(updated))

    @fastapi_app.delete("/api/trips/{trip_id}")
    def delete_trip(
        trip_id: str,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        existing = ctx.trip_repository.get(trip_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Trip not found")
        assert_trip_access(user, existing)
        ctx.trip_repository.delete(trip_id)
        ctx.audit_service.record(
            operator_id=user["id"], action="trip_deleted", target=trip_id, detail={}
        )
        return {"code": 200}

    @fastapi_app.post("/api/notifications/send")
    def send_notification(
        payload: NotificationSendRequest,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        template = None
        if payload.template_id:
            template = ctx.template_service.get_notification_template(payload.template_id)
            if template is None:
                raise HTTPException(status_code=404, detail="Template not found")
        if template is None:
            template = next(
                (
                    item
                    for item in ctx.template_service.list_notification_templates()
                    if item.is_active
                ),
                ctx.template_service.ensure_default_template(),
            )

        destination = payload.destination or "未指定行程"
        team_id = _resolve_team_id(payload.team, payload.team_id)
        if payload.trip_id:
            trip = ctx.trip_repository.get(payload.trip_id)
            if trip is not None:
                destination = trip.get("destination", destination)
                team_id = str(trip.get("team_id") or trip.get("team") or team_id)

        rendered = ctx.template_service.render_notification(
            template,
            {
                "customer_name": payload.customer_name or user.get("username", user["id"]),
                "destination": destination,
            },
        )
        task = NotificationTask(
            team_id=team_id,
            trip_id=payload.trip_id or "",
            customer_id=user["id"],
            rendered_content=rendered,
            idempotency_key=f"manual:{uuid4().hex}",
            primary_channel=_parse_channel(payload.channel),
            fallback_channel=Channel.WECHAT_WORK_GROUP,
        )
        dispatch_result = ctx.notification_service.dispatch(task)
        ctx.audit_service.record(
            operator_id=user["id"],
            action="notification_dispatched",
            target=payload.trip_id or "manual",
            detail={"ok": dispatch_result["ok"], "attempts": len(task.attempts)},
        )
        return _ok(
            {
                "ok": dispatch_result["ok"],
                "notification_id": task.id,
                "status": task.status.value,
            }
        )

    @fastapi_app.get("/api/notifications/history")
    def notification_history(
        limit: int = 20,
        trip_id: str | None = None,
        team_id: str | None = None,
        team: str | None = None,
        channel: str | None = None,
        status: str | None = None,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        customer_id = None if user.get("role") == "admin" else user["id"]
        resolved_team_id = _resolve_team_id(team, team_id)
        items = _query_notification_items(
            repository=ctx.notification_attempt_repository,
            limit=limit,
            trip_id=trip_id,
            team_id=resolved_team_id or None,
            customer_id=customer_id,
            channel=channel,
            status=status,
        )
        return _ok({"total": len(items), "items": items})

    @fastapi_app.get("/api/notifications/recent")
    def recent_notifications(
        limit: int = 10,
        trip_id: str | None = None,
        team_id: str | None = None,
        team: str | None = None,
        channel: str | None = None,
        status: str | None = None,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        customer_id = None if user.get("role") == "admin" else user["id"]
        resolved_team_id = _resolve_team_id(team, team_id)
        items = _query_notification_items(
            repository=ctx.notification_attempt_repository,
            limit=limit,
            trip_id=trip_id,
            team_id=resolved_team_id or None,
            customer_id=customer_id,
            channel=channel,
            status=status,
        )
        recent = [_to_recent_item(item) for item in items]
        return _ok({"total": len(recent), "items": recent})

    @fastapi_app.get("/api/trips/{trip_id}/timeline")
    def trip_timeline(
        trip_id: str,
        user: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        trip = ctx.trip_repository.get(trip_id)
        if trip is None:
            raise HTTPException(status_code=404, detail="Trip not found")
        assert_trip_access(user, trip)
        customer_id = None if user.get("role") == "admin" else user["id"]
        attempts = _query_notification_items(
            repository=ctx.notification_attempt_repository,
            limit=200,
            trip_id=trip_id,
            team_id=None,
            customer_id=customer_id,
        )
        logs = ctx.audit_service.repository.list_by_target_payload(trip_id)
        return _ok(
            {"trip": _serialize_trip(trip), "notification_attempts": attempts, "audit_logs": logs}
        )

    @fastapi_app.get("/api/dashboard/stats")
    def dashboard_stats(
        _: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        attempts = ctx.notification_attempt_repository.list_history(limit=9999)
        sent = sum(1 for item in attempts if item.get("ok") is True)
        total = len(attempts)
        return _ok(
            {
                "today_notifications": total,
                "active_trips": len(
                    [t for t in ctx.trip_repository.list() if t.get("status") != "已完成"]
                ),
                "total_users": len(ctx.auth_service.users),
                "pending_complaints": 0,
                "notification_success_rate": round((sent / total) * 100, 1) if total else 0.0,
            }
        )

    @fastapi_app.get("/api/analytics/metrics")
    def analytics_metrics(
        _: dict[str, str] = Depends(get_current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> dict[str, Any]:
        attempts = ctx.notification_attempt_repository.list_history(limit=9999)
        sent = sum(1 for item in attempts if item.get("ok") is True)
        total = len(attempts)
        success_rate = f"{round((sent / total) * 100, 1) if total else 0.0}%"
        return _ok(
            {
                "metrics": {
                    "notification_success_rate": success_rate,
                    "avg_response_time": "1.2s",
                    "wow_growth": "+0.0%",
                    "user_satisfaction": "4.5/5",
                },
                "channel_performance": [],
                "top_trips": [],
            }
        )

    return fastapi_app


app = create_app()


def reset_state(purge_persistence: bool = False) -> None:
    store = JsonFileStore()
    if purge_persistence:
        store.clear_all()
    app.state.ctx = _build_context(store=store)


def dispatch_request(
    method: str, path: str, headers: dict[str, str] | None = None, body: str = ""
) -> Response:
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.request(method, path, headers=headers or {}, data=body)
    payload: dict[str, Any]
    if response.content:
        payload = response.json()
    else:
        payload = {"code": response.status_code}
    return Response(status=response.status_code, body=payload)


def run_http_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    uvicorn.run(app, host=host, port=port)
