import threading
from _thread import LockType
from collections.abc import Sequence
from typing import cast

import numpy as np
from fast_alpr import ALPR
from open_image_models.detection.core.hub import PlateDetectorModel

from app.core.config import settings
from app.schemas import BoundingBox, LicensePlate


def _mean(value: float | Sequence[float]) -> float:
    if isinstance(value, int | float):
        return float(value)
    return float(np.mean(value))


class PlateRecognizer:
    def __init__(self) -> None:
        self._alpr: ALPR = ALPR(
            detector_model=cast(PlateDetectorModel, settings.detector_model),
            ocr_model=settings.ocr_model,
            ocr_device="cpu",
        )
        self._lock: LockType = threading.Lock()

    def recognize(self, img: np.ndarray) -> list[LicensePlate]:
        with self._lock:
            results = self._alpr.predict(img)

        plates: list[LicensePlate] = []

        for r in results:
            if r.ocr is None or not r.ocr.text:
                continue

            bb = r.detection.bounding_box
            raw_text = r.ocr.text

            plates.append(
                LicensePlate(
                    plate_number=raw_text.replace("_", ""),
                    raw_text=raw_text,
                    plate_confidence=_mean(r.ocr.confidence),
                    detection_confidence=float(r.detection.confidence),
                    bbox=BoundingBox(
                        x1=int(bb.x1),
                        y1=int(bb.y1),
                        x2=int(bb.x2),
                        y2=int(bb.y2),
                    ),
                )
            )

        plates.sort(key=lambda plate: plate.plate_confidence, reverse=True)
        return plates
