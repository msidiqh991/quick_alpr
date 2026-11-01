import warnings
from io import BytesIO
from typing import TypeAlias, cast

import cv2
import numpy
from PIL import Image, UnidentifiedImageError

from app.core.errors import ImageDimensionsTooLargeError, InvalidImageError

BgrImage: TypeAlias = numpy.ndarray[
    tuple[int, int, int],
    numpy.dtype[numpy.uint8],
]


def _validate_dimensions(
    width: int,
    height: int,
    *,
    max_image_width: int,
    max_image_height: int,
    max_image_pixels: int,
) -> None:
    if (
        width <= 0
        or height <= 0
        or width > max_image_width
        or height > max_image_height
        or width * height > max_image_pixels
    ):
        raise ImageDimensionsTooLargeError


def decode_image(
    data: bytes,
    *,
    max_image_width: int,
    max_image_height: int,
    max_image_pixels: int,
) -> BgrImage:
    """Decode image bytes into a contiguous uint8 BGR OpenCV image."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as encoded_image:
                width, height = encoded_image.size
    except Image.DecompressionBombError as exc:
        raise ImageDimensionsTooLargeError from exc
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        raise InvalidImageError from exc

    _validate_dimensions(
        width,
        height,
        max_image_width=max_image_width,
        max_image_height=max_image_height,
        max_image_pixels=max_image_pixels,
    )

    buffer = numpy.frombuffer(data, dtype=numpy.uint8)
    img = cast(BgrImage | None, cv2.imdecode(buffer, cv2.IMREAD_COLOR))

    if img is None:
        raise InvalidImageError

    decoded_height, decoded_width = img.shape[:2]
    _validate_dimensions(
        decoded_width,
        decoded_height,
        max_image_width=max_image_width,
        max_image_height=max_image_height,
        max_image_pixels=max_image_pixels,
    )

    return numpy.ascontiguousarray(img, dtype=numpy.uint8)
