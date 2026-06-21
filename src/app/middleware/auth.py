"""认证中间件 — FastAPI Dependency."""

from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, str]:
    """从请求中提取当前用户。如果没有 token，返回默认匿名用户。"""
    ctx = getattr(request.app.state, "ctx", None)
    if ctx is not None and credentials is not None:
        try:
            token = credentials.credentials
            user = ctx.auth_service.verify(token)
            if user:
                return user
        except Exception:
            pass
    return {"id": "anonymous", "role": "viewer", "username": "anonymous"}


async def require_admin(
    user: dict[str, str] = Depends(get_current_user),
) -> dict[str, str]:
    """要求管理员权限的依赖。"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return user
