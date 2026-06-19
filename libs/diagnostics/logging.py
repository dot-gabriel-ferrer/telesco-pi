"""Structured logging helpers."""

from __future__ import annotations

import contextvars
import json
import logging
from datetime import datetime, timezone
from typing import Any


request_id_context: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id",
    default=None,
)


class JsonFormatter(logging.Formatter):
    """Small JSON formatter for log records."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = request_id_context.get()
        if request_id:
            payload["request_id"] = request_id
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            payload["extra"] = record.extra
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level.upper())


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def set_request_id(request_id: str | None) -> None:
    request_id_context.set(request_id)


def get_request_id() -> str | None:
    return request_id_context.get()

