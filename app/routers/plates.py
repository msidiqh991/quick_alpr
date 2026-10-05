from time import perf_counter
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.config import settings
from app.dependencies import PlateRecognizerDep
from app.schemas import ImageMetadata, RecognitionData, RecognizeResult
from app.utils.image import decode_image

router = APIRouter(prefix="/plates", tags=["Plates"])


@router.post(
    "/recognize",
    response_model=RecognizeResult,
    summary="Recognize license plates from an image",
    responses={
        413: {"description": "Image size exceeds limit"},
        422: {"description": "Invalid or unreadable image"},
    },
)
def recognize_plates(
    image: Annotated[UploadFile, File(description="Image file to recognize")],
    recognizer: PlateRecognizerDep,
) -> RecognizeResult:
    started_at = perf_counter()

    data = image.file.read(settings.max_upload_bytes + 1)

    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail="Ukuran gambar melebihi batas",
        )

    img = decode_image(data)

    height: int = img.shape[0]
    width: int = img.shape[1]

    plates = recognizer.recognize(img)

    return RecognizeResult(
        data=RecognitionData(
            plates=plates,
            processing_time=perf_counter() - started_at,
            image=ImageMetadata(
                filename=image.filename,
                width=width,
                height=height,
                content_type=image.content_type or "application/octet-stream",
            ),
        )
    )
