"""RBAC 权限中间件 — FastAPI Dependency."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException


def require_permission(user: dict[str, str], permission: str) -> None:
    """检查用户是否拥有指定权限。简单实现，admin 拥有所有权限。"""
    if user.get("role") == "admin":
        return
    permissions = user.get("permissions", [])
    if isinstance(permissions, str):
        permissions = [p.strip() for p in permissions.split(",")]
    if permission not in permissions:
        raise HTTPException(status_code=403, detail=f"Missing permission: {permission}")


def assert_tenant_scope(user: dict[str, str], tenant_id: str) -> None:
    """检查用户是否属于指定租户。admin 可以跨租户。"""
    if user.get("role") == "admin":
        return
    user_tenant = user.get("tenant_id", "")
    if user_tenant and user_tenant != tenant_id:
        raise HTTPException(status_code=403, detail="Cross-tenant access denied")
