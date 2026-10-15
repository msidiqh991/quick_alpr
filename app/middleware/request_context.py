import logging
import re
from contextvars import ContextVar, Token
from time import perf_counter
from typing import cast, final
from uuid import uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)

_REQUEST_ID_HEADER = b"x-request-id"
_REQUEST_ID_PATTERN = re.compile(rb"[A-Za-z0-9][A-Za-z0-9._:-]{0,63}")

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    """Return the request ID associated with the current execution context."""
    return _request_id.get()


@final
class RequestContextMiddleware:
    """Attach correlation metadata and one completion log to HTTP requests."""

    def __init__(self, app: ASGIApp) -> None:
        self.app: ASGIApp = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = cast(list[tuple[bytes, bytes]], scope.get("headers", []))
        request_id = _request_id_from_headers(headers) or str(uuid4())
        started_at = perf_counter()
        state = cast(dict[str, object], scope.setdefault("state", {}))
        state["request_id"] = request_id
        state["request_started_at"] = started_at
        token = _request_id.set(request_id)
        status_code = 500

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code

            if message["type"] == "http.response.start":
                status_code = cast(int, message["status"])
                response_headers = [
                    (name, value)
                    for name, value in cast(
                        list[tuple[bytes, bytes]],
                        message.get("headers", []),
                    )
                    if name.lower() != _REQUEST_ID_HEADER
                ]
                response_headers.append(
                    (_REQUEST_ID_HEADER, request_id.encode("ascii"))
                )
                message = {**message, "headers": response_headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            _log_completion(scope, request_id, status_code, started_at)
            _reset_request_id(token)


def _request_id_from_headers(headers: list[tuple[bytes, bytes]]) -> str | None:
    values = [value for name, value in headers if name.lower() == _REQUEST_ID_HEADER]
    if len(values) != 1 or _REQUEST_ID_PATTERN.fullmatch(values[0]) is None:
        return None

    return values[0].decode("ascii")


def _log_completion(
    scope: Scope,
    request_id: str,
    status_code: int,
    started_at: float,
) -> None:
    logger.info(
        "HTTP request completed: request_id=%s method=%s path=%s status_code=%d duration_ms=%.2f",
        request_id,
        cast(str, scope.get("method", "")),
        cast(str, scope.get("path", "")),
        status_code,
        (perf_counter() - started_at) * 1000,
    )


def _reset_request_id(token: Token[str | None]) -> None:
    _request_id.reset(token)
