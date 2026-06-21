from fastapi import APIRouter

from app.routes.workflow_routes import router as workflow_router
from app.routes.guest_routes import router as guest_router

__all__ = ["workflow_router", "guest_router"]
