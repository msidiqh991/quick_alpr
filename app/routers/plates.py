from time import perf_counter
from typing import cast

from fastapi import APIRouter, Request

from app.dependencies import AdmittedRuntimeDep, ValidatedUploadDep
from app.schemas import ImageMetadata, RecognitionData, RecognizeResult

router = APIRouter(prefix="/plates", tags=["Plates"])


@router.post(
    "/recognize",
    response_model=RecognizeResult,
    summary="Recognize license plates from an image",
    responses={
        413: {"description": "Image size exceeds limit"},
        422: {"description": "Invalid or unreadable image"},
        503: {
            "description": "Inference capacity is temporarily unavailable",
            "headers": {
                "Retry-After": {
                    "description": "Seconds to wait before retrying",
                    "schema": {"type": "integer"},
                }
            },
        },
        500: {"description": "Plate recognition inference failed"},
    },
)
async def recognize_plate_upload(
    request: Request,
    image: ValidatedUploadDep,
    runtime: AdmittedRuntimeDep,
) -> RecognizeResult:
    fallback_started_at = perf_counter()
    state_started_at = cast(
        object,
        getattr(request.state, "request_started_at", None),
    )
    started_at = (
        float(state_started_at)
        if isinstance(state_started_at, (int, float))
        else fallback_started_at
    )
    inference = await runtime.run(image.data)

    return RecognizeResult(
        data=RecognitionData(
            plates=list(inference.plates),
            processing_time=max(0.0, perf_counter() - started_at),
            image=ImageMetadata(
                filename=image.filename,
                width=inference.width,
                height=inference.height,
                content_type=image.content_type,
            ),
        )
    )
