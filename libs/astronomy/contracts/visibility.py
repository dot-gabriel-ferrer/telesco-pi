"""Visibility windows and target scoring contracts."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class VisibilityWindow(BaseModel):
    start_utc: datetime | None = None
    end_utc: datetime | None = None
    peak_alt_utc: datetime | None = None
    peak_alt_deg: float = 0.0
    is_visible: bool = False


class ScoreContribution(BaseModel):
    name: str
    score: float
    weight: float
    explanation: str


class TargetScore(BaseModel):
    target_id: str
    total_score: float
    contributions: list[ScoreContribution] = Field(default_factory=list)
    explanation: str = ''
