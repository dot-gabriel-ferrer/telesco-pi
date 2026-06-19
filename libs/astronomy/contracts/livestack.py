"""Contracts for live stacking runtime state and configuration."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class StackConfig(BaseModel):
    accumulation_method: Literal['mean', 'median', 'kappa_sigma'] = 'mean'
    kappa: float = 2.0
    min_frames: int = 3
    max_frames_in_memory: int = 32
    stretch_method: Literal['asinh', 'linear'] = 'asinh'
    source_retention_policy: Literal['keep_all', 'keep_best_n', 'discard'] = 'keep_best_n'


class RejectionReason(BaseModel):
    frame_id: str
    reason: str
    metric_value: float


class LiveStackState(BaseModel):
    stack_id: str
    state: str
    reference_frame_id: str | None = None
    accepted_frames: list[str] = Field(default_factory=list)
    rejected_frames: list[str] = Field(default_factory=list)
    rejection_reasons: list[RejectionReason] = Field(default_factory=list)
    alignment_quality_mean: float = 0.0
    preview_artifact_path: str | None = None
    config: StackConfig = Field(default_factory=StackConfig)
    session_persistence_path: str | None = None
    limitations: list[str] = Field(default_factory=list)
