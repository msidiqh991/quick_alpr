from typing import Literal, Protocol

import numpy as np


class BoundingBox(Protocol):
    x1: int
    y1: int
    x2: int
    y2: int


class DetectionResult(Protocol):
    bounding_box: BoundingBox
    confidence: float


class OcrResult(Protocol):
    text: str
    confidence: float | list[float]


class ALPRResult(Protocol):
    detection: DetectionResult
    ocr: OcrResult | None


class ALPR:
    def __init__(
        self,
        *,
        detector_model: str,
        ocr_model: str,
        ocr_device: Literal["cpu", "cuda", "auto"] = "auto",
    ) -> None: ...

    def predict(self, frame: np.ndarray) -> list[ALPRResult]: ...
