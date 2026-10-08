class AlprError(Exception):
    """Base exception for expected ALPR request failures."""


class ImageTooLargeError(AlprError):
    pass


class InvalidImageError(AlprError):
    pass
