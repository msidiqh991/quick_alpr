from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.dependencies import ReadinessDep

router = APIRouter(tags=["Health"])


@router.get("/", summary="Initial page of ALPR Service")
async def __init__() -> str:
    return "Initial ALPR (Automatic License Plate Recognition) Services"

@router.get(
    "/health",
    summary="Compatibility Readiness Check",
    responses={503: {"description": "Application initialization is incomplete"}},
)
async def ready(readiness: ReadinessDep) -> JSONResponse:
    if readiness:
        return JSONResponse({"status": "ready"})

    return JSONResponse(
        {"status": "not ready"},
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    )
