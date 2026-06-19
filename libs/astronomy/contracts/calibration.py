"""Calibration request and response contracts."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .common import RequestEnvelope


class CalibrationRequest(RequestEnvelope):
    observer_lat_deg: float
    observer_lon_deg: float
    target_id: str
    mount_az_deg_guess: float
    mount_alt_deg_guess: float


class CalibrationResponse(BaseModel):
    status: str
    confidence: float = 0.0
    offset_az_deg: float = 0.0
    offset_alt_deg: float = 0.0
    notes: list[str] = Field(default_factory=list)
