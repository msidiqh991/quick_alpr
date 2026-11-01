import logging
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.core.config import InitialConfig, load_initial_config
from app.core.errors import ImageTooLargeError, InvalidImageError
from app.core.exception_handlers import (
    image_too_large_handler,
    invalid_image_handler,
    unhandled_exception_handler,
)
from app.middleware import RequestBodyLimitMiddleware, RequestContextMiddleware
from app.routers import api_router
from app.services import PlateRecognizer
from app.services.inference_runtime import InferenceRuntime, Recognizer

RecognizerFactory = Callable[[InitialConfig], Recognizer]
logger = logging.getLogger(__name__)


def create_app(
    config: InitialConfig | None = None,
    *,
    recognizer_factory: RecognizerFactory = PlateRecognizer,
) -> FastAPI:
    """Create one configured service application."""
    initial_config = config if config is not None else load_initial_config()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncGenerator[None]:
        """Initialize shared application services during startup."""
        try:
            recognizer = recognizer_factory(initial_config)
            application.state.inference_runtime = InferenceRuntime(
                recognizer,
                initial_config,
            )
            logger.info(
                "ALPR models initialized: detector_model=%s ocr_model=%s",
                initial_config.detector_model,
                initial_config.ocr_model,
            )
            application.state.ready = True
            yield
        finally:
            application.state.ready = False

    application = FastAPI(
        title=initial_config.app_title,
        lifespan=lifespan,
        docs_url=initial_config.docs_url if initial_config.docs_enabled else None,
        redoc_url=initial_config.redoc_url if initial_config.docs_enabled else None,
        openapi_url=(
            initial_config.openapi_url if initial_config.docs_enabled else None
        ),
    )
    application.state.config = initial_config
    application.state.ready = False

    application.add_exception_handler(ImageTooLargeError, image_too_large_handler)
    application.add_exception_handler(InvalidImageError, invalid_image_handler)
    application.add_exception_handler(Exception, unhandled_exception_handler)

    application.add_middleware(
        RequestBodyLimitMiddleware,
        max_body_bytes=initial_config.max_total_request_bytes,
    )
    application.add_middleware(RequestContextMiddleware)

    application.include_router(api_router)
    return application


app = create_app()

def start() -> None:
    config = load_initial_config()
    uvicorn.run(
        "app.main:app",
        host=config.host,
        port=config.port,
        reload=config.reload,
        reload_dirs=[config.reload_dir] if config.reload else None,
    )
