from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Health Service Condition")
def health() -> dict[str, str]:
    return {"status": "ok"}
