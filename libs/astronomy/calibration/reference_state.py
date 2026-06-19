"""Calibration reference snapshots for persistence and review."""

from __future__ import annotations

from datetime import datetime, timezone
from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CalibrationReference(BaseModel):
    observer_lat_deg: float
    observer_lon_deg: float
    target_id: str
    created_at_utc: datetime = Field(default_factory=utcnow)
