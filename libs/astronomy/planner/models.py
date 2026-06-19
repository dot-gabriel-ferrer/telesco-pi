"""Internal planner models used for scheduling explanations."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class PlanItem(BaseModel):
    target_id: str
    start_utc: datetime
    end_utc: datetime
    score: float
    mode: str
    notes: list[str] = Field(default_factory=list)


class NightPlan(BaseModel):
    items: list[PlanItem] = Field(default_factory=list)
    summary: list[str] = Field(default_factory=list)
