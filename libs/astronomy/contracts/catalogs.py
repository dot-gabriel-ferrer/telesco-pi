"""Catalog-oriented contract models for fixed and orbital objects."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CatalogObject(BaseModel):
    id: str
    name: str
    kind: str
    ra_deg: float | None = None
    dec_deg: float | None = None
    magnitude: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TLERecord(BaseModel):
    name: str
    line1: str
    line2: str
    source: str = 'embedded'
    fetched_at_utc: datetime
