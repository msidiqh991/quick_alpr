from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Annotated, Protocol, TypeAlias, cast

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile

from app.core.config import InitialConfig
from app.core.errors import (
    ImageTooLargeError,
    InferenceOverloadedError,
    InferenceQueueTimeoutError,
)
from app.services.inference_runtime import InferenceRuntime


class AppState(Protocol):
    config: InitialConfig
    inference_runtime: InferenceRuntime
    ready: bool


@dataclass(frozen=True, slots=True)
class UploadedImage:
    data: bytes
    filename: str | None
    content_type: str


def _get_app_state(request: Request) -> AppState:
    application = cast(FastAPI, request.app)
    return cast(AppState, cast(object, application.state))


def get_config(request: Request) -> InitialConfig:
    """Return the validated configuration stored by the application factory."""
    return _get_app_state(request).config


def get_inference_runtime(request: Request) -> InferenceRuntime:
    """Return the lifespan-scoped inference runtime."""
    return _get_app_state(request).inference_runtime


async def get_readiness(request: Request) -> bool:
    """Return whether lifespan initialization completed successfully."""
    return _get_app_state(request).ready


ConfigDep: TypeAlias = Annotated[InitialConfig, Depends(get_config)]

ReadinessDep: TypeAlias = Annotated[bool, Depends(get_readiness)]

InferenceRuntimeDep: TypeAlias = Annotated[
    InferenceRuntime,
    Depends(get_inference_runtime),
]


async def get_admitted_runtime(
    runtime: InferenceRuntimeDep,
    config: ConfigDep,
) -> AsyncGenerator[InferenceRuntime]:
    """Reserve bounded runtime capacity for the full request operation."""
    try:
        async with runtime.admit():
            yield runtime
    except (InferenceOverloadedError, InferenceQueueTimeoutError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Inference capacity is temporarily unavailable",
            headers={"Retry-After": str(config.overload_retry_after_seconds)},
        ) from exc


AdmittedRuntimeDep: TypeAlias = Annotated[
    InferenceRuntime,
    Depends(get_admitted_runtime),
]


async def get_validated_upload(
    image: Annotated[UploadFile, File(description="Image file to recognize")],
    config: ConfigDep,
    _runtime: AdmittedRuntimeDep,
) -> UploadedImage:
    """Copy one bounded upload into immutable application-owned bytes."""
    try:
        data = await image.read(config.max_upload_bytes + 1)
        if len(data) > config.max_upload_bytes:
            raise ImageTooLargeError

        return UploadedImage(
            data=data,
            filename=image.filename,
            content_type=image.content_type or "application/octet-stream",
        )
    finally:
        await image.close()


ValidatedUploadDep: TypeAlias = Annotated[
    UploadedImage,
    Depends(get_validated_upload),
]
