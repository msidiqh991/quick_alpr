from functools import cache
from typing import ClassVar, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class InitialConfig(BaseSettings):
    """Define the single validated configuration used by one service process."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="ALPR_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application.
    app_title: str = Field(...)
    docs_url: str | None = None
    redoc_url: str | None = None
    openapi_url: str | None = None

    # Server.
    host: str = Field(...)
    port: int = Field(..., ge=1, le=65535)
    reload: bool = Field(...)
    reload_dir: str = Field(...)
    docs_enabled: bool = Field(...)

    # Bounded inference admission.
    inference_queue_limit: int = Field(default=4, ge=0, le=32)
    inference_queue_timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    overload_retry_after_seconds: int = Field(default=1, ge=1, le=60)

    # Models.
    detector_model: str = Field(...)
    ocr_model: str = Field(...)

    # Encoded request and decoded image limits.
    max_upload_mb: int = Field(default=5, gt=0, le=25)
    max_total_request_mb: int = Field(default=6, gt=0, le=26)
    max_image_width: int = Field(default=7680, gt=0, le=16384)
    max_image_height: int = Field(default=4320, gt=0, le=16384)
    max_image_pixels: int = Field(default=25_000_000, gt=0, le=100_000_000)

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def max_total_request_bytes(self) -> int:
        return self.max_total_request_mb * 1024 * 1024

    @model_validator(mode="after")
    def validate_request_limits(self) -> Self:
        if self.max_total_request_bytes <= self.max_upload_bytes:
            raise ValueError("max_total_request_mb must exceed max_upload_mb")
        return self


@cache
def load_initial_config() -> InitialConfig:
    """Load and cache configuration once for the current process."""
    return InitialConfig()  # pyright: ignore[reportCallIssue]
