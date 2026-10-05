from fastapi import APIRouter

from app.routers import health, plates

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(plates.router)

__all__ = ["api_router"]
