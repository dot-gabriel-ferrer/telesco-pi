"""Session-domain models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SessionSummary(BaseModel):
    id: str
    name: str
    status: str
    mode: str
    storage_path: str
    created_at: datetime
    opened_at: datetime
    closed_at: datetime | None = None
    last_error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

