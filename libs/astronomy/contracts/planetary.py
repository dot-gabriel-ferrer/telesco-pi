"""Planetary processing job configuration and quality summaries."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .common import QualityProfile


class PlanetaryJobConfig(BaseModel):
    profile: QualityProfile = QualityProfile.BALANCED
    frame_selection_fraction: float = 0.5
    sharpen_strength: float = 1.0


class FrameQuality(BaseModel):
    sharpness: float
    snr: float
    background: float
    centroid: tuple[float, float] | None = None
    score: float = 0.0
    notes: list[str] = Field(default_factory=list)
