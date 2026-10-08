from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.core.config import settings
from app.core.errors import ImageTooLargeError, InvalidImageError
from app.core.exception_handlers import (
    image_too_large_handler,
    invalid_image_handler,
    unhandled_exception_handler,
)
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
    docs_url=settings.docs_url if settings.docs_enabled else None,
    redoc_url=settings.redoc_url if settings.docs_enabled else None,
    openapi_url=settings.openapi_url if settings.docs_enabled else None,
)
app.add_exception_handler(ImageTooLargeError, image_too_large_handler)
app.add_exception_handler(InvalidImageError, invalid_image_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# Route Registers
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
