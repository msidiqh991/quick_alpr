import logging
from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from time import perf_counter
from typing import Protocol, final

from anyio import Semaphore, WouldBlock, move_on_after, to_thread

from app.core.config import InitialConfig
from app.core.errors import InferenceOverloadedError, InferenceQueueTimeoutError
from app.middleware import get_request_id
from app.schemas import LicensePlate
from app.utils.image import BgrImage, decode_image

logger = logging.getLogger(__name__)


class Recognizer(Protocol):
    def recognize(self, image: BgrImage) -> Sequence[LicensePlate]: ...


@dataclass(frozen=True, slots=True)
class InferenceResult:
    plates: tuple[LicensePlate, ...]
    width: int
    height: int
    queue_wait_seconds: float
    inference_seconds: float


@dataclass(frozen=True, slots=True)
class InferenceRuntimeSnapshot:
    admitted: int
    rejected: int
    timed_out: int
    completed: int


@final
class InferenceRuntime:
    def __init__(self, recognizer: Recognizer, config: InitialConfig) -> None:
        self._recognizer = recognizer
        self._config = config
        self._admission = Semaphore(config.inference_queue_limit + 1)
        self._active = Semaphore(1)
        self._admitted = 0
        self._rejected = 0
        self._timed_out = 0
        self._completed = 0

    @asynccontextmanager
    async def admit(self) -> AsyncGenerator[None]:
        """Reserve active-or-queued capacity without waiting for a slot."""
        try:
            self._admission.acquire_nowait()
        except WouldBlock:
            self._rejected += 1
            logger.warning(
                "inference_overloaded event=admission_rejected request_id=%s",
                get_request_id() or "unknown",
            )
            raise InferenceOverloadedError from None

        self._admitted += 1
        try:
            yield
        finally:
            self._admission.release()

    async def run(self, data: bytes) -> InferenceResult:
        """Wait for the active slot, then decode and recognize in one worker thread."""
        queue_started_at = perf_counter()
        active_acquired = False
        
        with move_on_after(self._config.inference_queue_timeout_seconds):
            await self._active.acquire()
            active_acquired = True

        if not active_acquired:
            self._timed_out += 1
            logger.warning(
                "inference_queue_timeout event=active_slot_timeout request_id=%s",
                get_request_id() or "unknown",
            )
            raise InferenceQueueTimeoutError from None

        queue_wait_seconds = perf_counter() - queue_started_at
        logger.info(
            "inference_started request_id=%s queue_wait_seconds=%.6f",
            get_request_id() or "unknown",
            queue_wait_seconds,
        )
        inference_started_at = perf_counter()
        try:
            plates, width, height = await to_thread.run_sync(
                self._run_sync,
                data,
                abandon_on_cancel=False,
            )
        except BaseException:
            logger.info(
                "inference_failed request_id=%s inference_seconds=%.6f",
                get_request_id() or "unknown",
                perf_counter() - inference_started_at,
            )
            raise
        else:
            self._completed += 1
        finally:
            self._active.release()

        inference_seconds = perf_counter() - inference_started_at
        logger.info(
            "inference_completed request_id=%s inference_seconds=%.6f image_width=%d image_height=%d detection_count=%d",
            get_request_id() or "unknown",
            inference_seconds,
            width,
            height,
            len(plates),
        )
        
        return InferenceResult(
            plates=plates,
            width=width,
            height=height,
            queue_wait_seconds=queue_wait_seconds,
            inference_seconds=inference_seconds,
        )

    def snapshot(self) -> InferenceRuntimeSnapshot:
        return InferenceRuntimeSnapshot(
            admitted=self._admitted,
            rejected=self._rejected,
            timed_out=self._timed_out,
            completed=self._completed,
        )

    def _run_sync(self, data: bytes) -> tuple[tuple[LicensePlate, ...], int, int]:
        image = decode_image(
            data,
            max_image_width=self._config.max_image_width,
            max_image_height=self._config.max_image_height,
            max_image_pixels=self._config.max_image_pixels,
        )
        height, width = image.shape[:2]
        plates = tuple(self._recognizer.recognize(image))
        return plates, width, height
