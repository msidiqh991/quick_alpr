from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/", summary="Initial page of ALPR Service")
def __init__() -> str:
    return "Initial ALPR (Automatic License Plate Recognition) Services"

@router.get("/health", summary="Health Service Condition")
def health() -> dict[str, str]:
    return {"status": "ok"}
