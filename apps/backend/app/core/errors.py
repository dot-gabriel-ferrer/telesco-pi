"""Application errors and exception handlers."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from apps.backend.app.api.schemas import ApiErrorResponse
from libs.diagnostics.logging import get_logger, get_request_id

logger = get_logger(__name__)


class AppError(RuntimeError):
    """Structured application error."""

    def __init__(self, code: str, message: str, status_code: int = 400, details: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        payload = ApiErrorResponse(
            error=exc.message,
            code=exc.code,
            request_id=get_request_id(),
            details=exc.details,
        )
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump(mode="json"))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        payload = ApiErrorResponse(
            error="Validation error.",
            code="validation_error",
            request_id=get_request_id(),
            details={"issues": exc.errors()},
        )
        return JSONResponse(status_code=422, content=payload.model_dump(mode="json"))

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled application error", extra={"extra": {"request_id": get_request_id()}})
        payload = ApiErrorResponse(
            error="Unexpected server error.",
            code="internal_server_error",
            request_id=get_request_id(),
        )
        return JSONResponse(status_code=500, content=payload.model_dump(mode="json"))

