from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.core.config import settings
from app.routers import api_router
from app.services import PlateRecognizer


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Initialize shared application services during startup."""
    app.state.plate_recognizer = PlateRecognizer()
    yield


app = FastAPI(
    title=settings.app_title,
    lifespan=lifespan,
    docs_url=settings.docs_url,
    redoc_url=settings.redoc_url,
    openapi_url=settings.openapi_url,
)
app.include_router(api_router)


def start_dev() -> None:
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        reload_dirs=[settings.reload_dir] if settings.reload else None,
    )


def start_prod() -> None:
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
    )
