"""Pipeline artifacts, manifests, and persisted job contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .common import AstronomyError, JobKind, JobState, QualityProfile, ResourceMetrics


class Artifact(BaseModel):
    id: str
    kind: str
    path: str
    size_bytes: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class PipelineManifest(BaseModel):
    pipeline_id: str
    name: str
    kind: JobKind
    version: str
    description: str
    input_kinds: list[str] = Field(default_factory=list)
    output_kinds: list[str] = Field(default_factory=list)
    supported_profiles: list[QualityProfile] = Field(default_factory=lambda: [QualityProfile.LOW, QualityProfile.BALANCED, QualityProfile.HIGH])


class JobRecord(BaseModel):
    job_id: str
    pipeline_id: str
    pipeline_version: str
    kind: JobKind
    state: JobState
    session_id: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    parameters: dict[str, Any] = Field(default_factory=dict)
    artifacts: list[Artifact] = Field(default_factory=list)
    metrics: ResourceMetrics = Field(default_factory=ResourceMetrics)
    failure: AstronomyError | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
