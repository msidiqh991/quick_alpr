from typing import Annotated, Protocol, TypeAlias, cast

from fastapi import Depends, FastAPI, Request

from app.services import PlateRecognizer


class AppState(Protocol):
    plate_recognizer: PlateRecognizer


def get_plate_recognizer(request: Request) -> PlateRecognizer:
    """Return the singleton recognizer created during application startup."""
    application = cast(FastAPI, request.app)
    state = cast(AppState, cast(object, application.state))
    return state.plate_recognizer


PlateRecognizerDep: TypeAlias = Annotated[
    PlateRecognizer,
    Depends(get_plate_recognizer),
]
