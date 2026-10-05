from typing import ClassVar

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Read from environment variables (or file .env)."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="ALPR_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application Configuration.
    app_title: str = Field(...)
    docs_url: str | None = None
    redoc_url: str | None = None
    openapi_url: str | None = None

    # Server Configuration for the ALPR system.
    host: str = Field(...)
    port: int = Field(...)
    reload: bool = Field(...)
    reload_dir: str = Field(...)
    docs_enabled: bool = Field(...)

    # Model configuration.
    detector_model: str = Field(...)
    ocr_model: str = Field(...)
    max_upload_mb: int = Field(...)

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


settings: Settings = Settings()  # pyright: ignore[reportCallIssue]
