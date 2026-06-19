"""Optional token auth middleware."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class OptionalAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, enabled: bool, token: str | None, api_prefix: str) -> None:
        super().__init__(app)
        self.enabled = enabled and bool(token)
        self.token = token
        self.api_prefix = api_prefix

    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)
        if not request.url.path.startswith(self.api_prefix):
            return await call_next(request)
        if request.url.path.endswith("/health/live") or request.url.path.endswith("/health/ready"):
            return await call_next(request)
        auth_header = request.headers.get("Authorization", "")
        expected = f"Bearer {self.token}" if self.token else ""
        if auth_header != expected:
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized", "code": "auth_required", "details": {}},
            )
        return await call_next(request)
