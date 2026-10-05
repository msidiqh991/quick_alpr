from typing import Annotated, Protocol, TypeAlias, cast

from fastapi import Depends, Request

from app.services import PlateRecognizer


class AppState(Protocol):
    plate_recognizer: PlateRecognizer


def get_plate_recognizer(request: Request) -> PlateRecognizer:
    """Return singleton ALPR recognizer yang dibuat saat application startup."""
    state = cast(AppState, request.app.state)
    return state.plate_recognizer


PlateRecognizerDep: TypeAlias = Annotated[
    PlateRecognizer,
    Depends(get_plate_recognizer),
]
