class AlprError(Exception):
    """Base exception for expected ALPR request failures."""


class ImageTooLargeError(AlprError):
    pass


class ImageDimensionsTooLargeError(ImageTooLargeError):
    pass


class InvalidImageError(AlprError):
    pass


class InferenceOverloadedError(AlprError):
    pass


class InferenceQueueTimeoutError(AlprError):
    pass
