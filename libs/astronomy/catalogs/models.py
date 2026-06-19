"""Catalog data models used by loaders and search utilities."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from libs.astronomy.domain.targets import SolarSystemBody, Target, TargetKind


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CatalogEntry(BaseModel):
    id: str
    name: str
    kind: TargetKind
    ra_deg: float | None = None
    dec_deg: float | None = None
    magnitude: float | None = None
    constellation: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    angular_size_arcmin: float | None = None
    body: SolarSystemBody | None = None

    def to_target(self) -> Target:
        return Target(**self.model_dump())


class TLEEntry(BaseModel):
    name: str
    line1: str
    line2: str
    source: str = 'embedded'
    fetched_at_utc: datetime = Field(default_factory=utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)
