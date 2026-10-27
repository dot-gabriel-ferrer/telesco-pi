"""Reject cross-site browser commands against a local hardware workstation."""

from urllib.parse import urlsplit

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class BrowserOriginMiddleware:
    def __init__(self, app: ASGIApp, allowed_origins: list[str]) -> None:
        self.app = app
        self.allowed_origins = set(allowed_origins)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        origin = headers.get("origin")
        allowed = origin is None or origin in self.allowed_origins
        if origin is not None and not allowed:
            try:
                parsed = urlsplit(origin)
                allowed = parsed.scheme in ("http", "https") and parsed.netloc == headers.get("host") and not parsed.path and not parsed.query and not parsed.fragment
            except ValueError:
                allowed = False
        if not allowed:
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 1008})
            else:
                await JSONResponse({"error": "Browser origin is not allowed.", "code": "origin_not_allowed"}, status_code=403)(scope, receive, send)
            return
        await self.app(scope, receive, send)
