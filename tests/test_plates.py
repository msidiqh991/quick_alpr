from collections.abc import Generator
from dataclasses import dataclass
from typing import Protocol

import cv2
import numpy as np
import pytest
from httpx2 import Response
from pytest import LogCaptureFixture, MonkeyPatch
from starlette.testclient import TestClient

import app.services.plate_recognizer as plate_recognizer_module
from app.core.config import settings
from app.dependencies import get_plate_recognizer
from app.main import app
from app.schemas import BoundingBox, LicensePlate, RecognizeResult
from app.services import PlateRecognizer
from app.utils.image import BgrImage


class ClientFactory(Protocol):
    def __call__(
        self,
        plates: list[LicensePlate] | None = None,
        *,
        raise_server_exceptions: bool = True,
    ) -> TestClient: ...


class FakeRecognizer:
    def __init__(self, plates: list[LicensePlate] | None = None) -> None:
        self.plates: list[LicensePlate] = plates or []

    def recognize(self, _img: BgrImage) -> list[LicensePlate]:
        return self.plates


class FailingRecognizer:
    def recognize(self, _img: BgrImage) -> list[LicensePlate]:
        raise RuntimeError("Simulated inference failure")


@pytest.fixture
def make_client() -> Generator[ClientFactory, None, None]:
    def _make(
        plates: list[LicensePlate] | None = None,
        *,
        raise_server_exceptions: bool = True,
    ) -> TestClient:
        app.dependency_overrides[get_plate_recognizer] = (
            lambda: FakeRecognizer(plates)
        )

        return TestClient(
            app,
            raise_server_exceptions=raise_server_exceptions,
        )

    yield _make
    app.dependency_overrides.clear()


def _png() -> bytes:
    ok, buffer = cv2.imencode(
        ".png",
        np.zeros((20, 40, 3), dtype=np.uint8),
    )
    assert ok

    return buffer.tobytes()


def _upload(
    client: TestClient,
    content: bytes = b"",
    name: str = "image.png",
    mime: str = "image/png",
) -> Response:
    return client.post(
        "/plates/recognize",
        files={"image": (name, content or _png(), mime)},
    )


def test_health(make_client: ClientFactory) -> None:
    response = make_client().get("/health")

    assert response.status_code == 200
    assert response.content == b'{"status":"ok"}'


def test_recognize_returns_plates(make_client: ClientFactory) -> None:
    plate = LicensePlate(
        plate_number="B1234ABC",
        raw_text="B_1234_ABC",
        plate_confidence=0.90,
        detection_confidence=0.95,
        bbox=BoundingBox(
            x1=1,
            y1=2,
            x2=3,
            y2=4,
        ),
    )

    response = _upload(make_client([plate]))
    assert response.status_code == 200
    result = RecognizeResult.model_validate_json(response.content)

    assert result.status == "success"
    assert result.data.plates[0].plate_number == "B1234ABC"
    assert result.data.plates[0].raw_text == "B_1234_ABC"
    assert result.data.plates[0].bbox == BoundingBox(x1=1, y1=2, x2=3, y2=4)


def test_no_plate_is_empty_list_not_error(make_client: ClientFactory) -> None:
    response = _upload(make_client())
    assert response.status_code == 200
    result = RecognizeResult.model_validate_json(response.content)
    assert result.data.plates == []


def test_too_large_is_413(
    make_client: ClientFactory,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "max_upload_mb", 0)
    response = _upload(make_client())
    assert response.status_code == 413


def test_missing_file_is_422(make_client: ClientFactory) -> None:
    response = make_client().post("/plates/recognize")
    assert response.status_code == 422


def test_unreadable_image_is_422(make_client: ClientFactory) -> None:
    response = _upload(make_client(), content=b"not-an-image")

    assert response.status_code == 422
    assert response.content == b'{"detail":"File could not be decoded as an image"}'


def test_inference_failure_is_logged_and_returns_500(
    make_client: ClientFactory,
    caplog: LogCaptureFixture,
) -> None:
    client = make_client(raise_server_exceptions=False)
    app.dependency_overrides[get_plate_recognizer] = FailingRecognizer

    response = _upload(client)

    assert response.status_code == 500
    assert response.content == (
        b'{"detail":"An error occurred while processing the image"}'
    )
    assert "Unhandled ALPR service error" in caplog.text


def test_recognizer_preserves_raw_ocr_text(monkeypatch: MonkeyPatch) -> None:
    @dataclass(frozen=True)
    class FakeBoundingBoxResult:
        x1: int = 1
        y1: int = 2
        x2: int = 30
        y2: int = 12

    @dataclass(frozen=True)
    class FakeDetectionResult:
        bounding_box: FakeBoundingBoxResult
        confidence: float

    @dataclass(frozen=True)
    class FakeOcrResult:
        text: str
        confidence: list[float]

    @dataclass(frozen=True)
    class FakeAlprResult:
        detection: FakeDetectionResult
        ocr: FakeOcrResult

    class FakeAlpr:
        def predict(self, _img: BgrImage) -> list[FakeAlprResult]:
            return [
                FakeAlprResult(
                    detection=FakeDetectionResult(
                        bounding_box=FakeBoundingBoxResult(),
                        confidence=0.95,
                    ),
                    ocr=FakeOcrResult(
                        text="B_1234_ABC",
                        confidence=[0.8, 1.0],
                    ),
                )
            ]

    def make_fake_alpr(**_kwargs: object) -> FakeAlpr:
        return FakeAlpr()

    monkeypatch.setattr(
        plate_recognizer_module,
        "ALPR",
        make_fake_alpr,
    )
    recognizer = PlateRecognizer()

    plates = recognizer.recognize(np.zeros((20, 40, 3), dtype=np.uint8))

    assert len(plates) == 1
    assert plates[0].raw_text == "B_1234_ABC"
    assert plates[0].plate_number == "B1234ABC"
    assert plates[0].plate_confidence == pytest.approx(0.9)


def test_old_versioned_endpoint_is_gone(make_client: ClientFactory) -> None:
    response = make_client().post("/api/v1/detect")
    assert response.status_code == 404
