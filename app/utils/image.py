from typing import TypeAlias

import cv2
import numpy

from app.core.errors import InvalidImageError

BgrImage: TypeAlias = numpy.ndarray[
    tuple[int, int, int],
    numpy.dtype[numpy.uint8],
]


def decode_image(data: bytes) -> BgrImage:
    """Decode image bytes into a contiguous uint8 BGR OpenCV image."""
    buffer = numpy.frombuffer(data, dtype=numpy.uint8)
    img = cv2.imdecode(buffer, cv2.IMREAD_COLOR)

    if img is None:
        raise InvalidImageError

    return numpy.ascontiguousarray(img, dtype=numpy.uint8)


def apply_clahe(
    img: BgrImage,
    *,
    clip_limit: float = 2.0,
    tile_grid_size: tuple[int, int] = (8, 8),
) -> BgrImage:
    """Apply CLAHE to image luminance and return a BGR image."""
    if clip_limit <= 0:
        raise ValueError("clip_limit must be greater than zero")

    if min(tile_grid_size) <= 0:
        raise ValueError("tile_grid_size values must be greater than zero")

    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    luminance, channel_a, channel_b = cv2.split(lab)
    clahe = cv2.createCLAHE(
        clipLimit=clip_limit,
        tileGridSize=tile_grid_size,
    )
    enhanced_lab = cv2.merge((clahe.apply(luminance), channel_a, channel_b))
    enhanced = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

    return numpy.ascontiguousarray(enhanced, dtype=numpy.uint8)
