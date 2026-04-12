from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class PermissionDenied(Exception):
    message: str
    code: str = "permission_denied"


_ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {
        "trip:read",
        "trip:write",
        "notification:read",
        "notification:write",
        "rule:read",
        "rule:write",
        "rule:approve",
        "template:read",
        "template:write",
        "audit:read",
        "ops:read",
    },
    "ops": {
        "trip:read",
        "notification:read",
        "notification:write",
        "rule:read",
        "template:read",
        "audit:read",
        "ops:read",
    },
    "concierge": {
        "trip:read",
        "notification:read",
        "notification:write",
        "template:read",
    },
    "cs": {
        "trip:read",
        "notification:read",
        "audit:read",
    },
    "sales": {"trip:read", "notification:read"},
    "user": {"trip:read", "trip:write", "notification:read", "notification:write"},
}


def _safe_role(user: dict[str, str]) -> str:
    return str(user.get("role") or "").strip().lower()


def allowed_permissions(user: dict[str, str]) -> set[str]:
    role = _safe_role(user)
    return set(_ROLE_PERMISSIONS.get(role, set()))


def require_permission(user: dict[str, str], permission: str) -> None:
    if permission in allowed_permissions(user):
        return
    raise PermissionDenied(message=f"Missing permission: {permission}", code="missing_permission")


def require_any_permission(user: dict[str, str], permissions: Iterable[str]) -> None:
    granted = allowed_permissions(user)
    for permission in permissions:
        if permission in granted:
            return
    raise PermissionDenied(message="Missing required permission set", code="missing_permission")


def assert_tenant_scope(user: dict[str, str], target_tenant_id: str) -> None:
    tenant_id = str(user.get("tenant_id") or "").strip()
    if not tenant_id or not target_tenant_id or tenant_id != str(target_tenant_id).strip():
        raise PermissionDenied(message="Cross-tenant access denied", code="cross_tenant_forbidden")


def assert_team_scope(user: dict[str, str], target_team_id: str, *, allow_admin: bool = True) -> None:
    role = _safe_role(user)
    if allow_admin and role == "admin":
        return
    team_id = str(user.get("team_id") or "").strip()
    if team_id and team_id == str(target_team_id).strip():
        return
    if not team_id:
        # Users without explicit team binding are permitted to operate within tenant scope.
        return
    raise PermissionDenied(message="Cross-team access denied", code="cross_team_forbidden")
