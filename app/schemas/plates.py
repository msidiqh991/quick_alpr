from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field


class BoundingBox(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    x1: int = Field(ge=0)
    y1: int = Field(ge=0)
    x2: int = Field(ge=0)
    y2: int = Field(ge=0)


class ImageMetadata(BaseModel):
    filename: str | None = None
    content_type: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class LicensePlate(BaseModel):
    plate_number: str = Field(description="The plate number of the license plate")
    raw_text: str | None = Field(
        default=None,
        description="OCR result before normalization/formatting.",
    )
    plate_confidence: float = Field(
        ge=0, le=1, description="The confidence score of the plate number"
    )
    detection_confidence: float = Field(
        ge=0, le=1, description="The confidence score of the license plate detection"
    )
    bbox: BoundingBox


class RecognitionData(BaseModel):
    plates: list[LicensePlate]
    image: ImageMetadata
    processing_time: float = Field(ge=0)


class RecognizeResult(BaseModel):
    status: Literal["success"] = "success"
    data: RecognitionData
