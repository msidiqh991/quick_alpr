from typing import TypeAlias

import cv2
import numpy

BgrImage: TypeAlias = numpy.ndarray[
    tuple[int, int, int],
    numpy.dtype[numpy.uint8],
]


def decode_image(data: bytes) -> BgrImage:
    """Decode image bytes into a contiguous uint8 BGR OpenCV image."""
    buffer = numpy.frombuffer(data, dtype=numpy.uint8)
    img = cv2.imdecode(buffer, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Failed to decode image, data: " + str(data))

    return numpy.ascontiguousarray(img, dtype=numpy.uint8)
