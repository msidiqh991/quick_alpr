from collections.abc import Sequence
from typing import cast, final

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


@final
class RequestBodyLimitMiddleware:
    """Reject HTTP request bodies that exceed a configured byte limit."""

    def __init__(self, app: ASGIApp, max_body_bytes: int) -> None:
        if max_body_bytes <= 0:
            raise ValueError("max_body_bytes must be positive")

        self.app: ASGIApp = app
        self.max_body_bytes: int = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = cast(list[tuple[bytes, bytes]], scope.get("headers", []))
        content_lengths = _header_values(headers, b"content-length")

        if content_lengths:
            content_length = _parse_content_length(content_lengths)
            if content_length is None:
                await _invalid_content_length_response(scope, receive, send)
                return
            if content_length > self.max_body_bytes:
                await _body_too_large_response(scope, receive, send)
                return

        bytes_received = 0
        body_too_large = False
        replace_downstream_response = False
        downstream_response_started = False

        async def limited_receive() -> Message:
            nonlocal bytes_received, body_too_large, replace_downstream_response

            if body_too_large:
                return {"type": "http.disconnect"}

            message = await receive()
            if message["type"] == "http.request":
                body = cast(bytes, message.get("body", b""))
                bytes_received += len(body)
                if bytes_received > self.max_body_bytes:
                    body_too_large = True
                    replace_downstream_response = not downstream_response_started
                    return {"type": "http.disconnect"}

            return message

        async def limited_send(message: Message) -> None:
            nonlocal downstream_response_started

            if replace_downstream_response:
                return
            if message["type"] == "http.response.start":
                downstream_response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, limited_send)
        except Exception:
            if not body_too_large:
                raise

        if replace_downstream_response:
            await _body_too_large_response(scope, receive, send)


def _header_values(
    headers: Sequence[tuple[bytes, bytes]],
    name: bytes,
) -> list[bytes]:
    return [value for key, value in headers if key.lower() == name]


def _parse_content_length(values: list[bytes]) -> int | None:
    if len(values) != 1 or not values[0] or not values[0].isascii():
        return None
    if any(byte < ord("0") or byte > ord("9") for byte in values[0]):
        return None
    try:
        return int(values[0])
    except ValueError:
        return None


async def _body_too_large_response(
    scope: Scope,
    receive: Receive,
    send: Send,
) -> None:
    response = JSONResponse(
        status_code=413,
        content={"detail": "Request body exceeds the allowed limit"},
    )
    await response(scope, receive, send)


async def _invalid_content_length_response(
    scope: Scope,
    receive: Receive,
    send: Send,
) -> None:
    response = JSONResponse(
        status_code=400,
        content={"detail": "Invalid Content-Length header"},
    )
    await response(scope, receive, send)
