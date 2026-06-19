"""Planner request/response contracts for night scheduling."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .common import RequestEnvelope


class EquipmentSpec(BaseModel):
    focal_length_mm: float = Field(gt=0)
    aperture_mm: float = Field(gt=0)
    mount_type: str = 'alt_az'
    camera_pixel_size_um: float | None = None
    camera_resolution: tuple[int, int] | None = None


class ObserverSpec(BaseModel):
    lat_deg: float
    lon_deg: float
    elevation_m: float = 0.0
    timezone_name: str = 'UTC'


class TimeWindow(BaseModel):
    start_utc: datetime
    end_utc: datetime


class TargetRef(BaseModel):
    id: str
    kind: str
    tags: list[str] = Field(default_factory=list)
    ra_deg: float | None = None
    dec_deg: float | None = None
    tle_name: str | None = None


class PlannerConstraints(BaseModel):
    min_alt_deg: float = 10.0
    max_airmass: float | None = None
    moon_sep_min_deg: float = 20.0
    local_horizon_mask: dict[int, float] = Field(default_factory=dict)


class PlannerRequest(RequestEnvelope):
    observer: ObserverSpec
    equipment: EquipmentSpec
    night_window: TimeWindow
    targets: list[TargetRef]
    constraints: PlannerConstraints = Field(default_factory=PlannerConstraints)
    mode: Literal['mixed', 'planetary', 'eaa', 'orbital'] = 'mixed'


class ScoreFactor(BaseModel):
    name: str
    value: float
    weight: float
    explanation: str


class PlanItem(BaseModel):
    target_id: str
    recommended_start_utc: datetime
    recommended_end_utc: datetime
    score_total: float
    score_factors: list[ScoreFactor] = Field(default_factory=list)
    mode: str
    risks: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class PlannerDiagnostics(BaseModel):
    sun_alt_deg: float
    moon_alt_deg: float
    moon_illumination: float
    rejected_targets: list[str] = Field(default_factory=list)
    stale_data_flags: list[str] = Field(default_factory=list)


class PlannerResponse(BaseModel):
    status: str
    plan_items: list[PlanItem] = Field(default_factory=list)
    explanations: list[str] = Field(default_factory=list)
    diagnostics: PlannerDiagnostics
