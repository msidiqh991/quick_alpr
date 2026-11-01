import threading
from _thread import LockType
from collections.abc import Sequence
from typing import cast

import numpy as np
from fast_alpr import ALPR
from fast_plate_ocr.inference.hub import OcrModel
from open_image_models.detection.core.hub import PlateDetectorModel

from app.core.config import InitialConfig
from app.schemas import BoundingBox, LicensePlate
from app.utils.image import BgrImage
from app.utils.plate import normalize_plate


def _mean(value: float | Sequence[float]) -> float:
    if isinstance(value, int | float):
        return float(value)
    return float(np.mean(value))


class PlateRecognizer:
    def __init__(self, config: InitialConfig) -> None:
        self._alpr: ALPR = ALPR(
            detector_model=cast(PlateDetectorModel, config.detector_model),
            ocr_model=cast(OcrModel, config.ocr_model),
            ocr_device="cpu",
        )
        self._lock: LockType = threading.Lock()

    def recognize(self, image: BgrImage) -> list[LicensePlate]:
        with self._lock:
            results = self._alpr.predict(image)

        plates: list[LicensePlate] = []

        for res in results:
            if res.ocr is None or not res.ocr.text:
                continue

            bb = res.detection.bounding_box
            raw_text = res.ocr.text

            plates.append(
                LicensePlate(
                    plate_number=normalize_plate(raw_text),
                    raw_text=raw_text,
                    plate_confidence=_mean(res.ocr.confidence),
                    detection_confidence=float(res.detection.confidence),
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
