"""Orbital tracking request/response contracts built on TLE propagation."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from .common import RequestEnvelope


class TrackPoint(BaseModel):
    utc: datetime
    az_deg: float
    alt_deg: float


class OrbitalPass(BaseModel):
    object_id: str
    object_name: str
    tle_epoch_utc: datetime
    tle_age_hours: float
    pass_start_utc: datetime
    pass_peak_utc: datetime
    pass_end_utc: datetime
    peak_alt_deg: float
    az_alt_track: list[TrackPoint] = Field(default_factory=list)
    visibility_class: str
    tracking_warnings: list[str] = Field(default_factory=list)
    capture_window_recommendation: str
    mount_command_rate_hz: float


class TLEContract(BaseModel):
    name: str
    source: str
    age_hours: float
    fresh: bool


class OrbitalRequest(RequestEnvelope):
    object_names: list[str]
    start_utc: datetime
    end_utc: datetime
    observer_lat_deg: float
    observer_lon_deg: float
    observer_elevation_m: float = 0.0
    min_alt_deg: float = 10.0


class OrbitalResponse(BaseModel):
    status: str
    passes: list[OrbitalPass] = Field(default_factory=list)
    tle_freshness: list[TLEContract] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
