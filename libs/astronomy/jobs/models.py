"""Job-state models for astronomy processing jobs."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from libs.astronomy.contracts.common import AstronomyError, JobKind, ResourceMetrics
from libs.astronomy.contracts.pipelines import Artifact


class JobState(str, Enum):
    QUEUED = 'queued'
    RUNNING = 'running'
    PAUSED = 'paused'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class JobMetrics(ResourceMetrics):
    pass


class JobRecord(BaseModel):
    job_id: str
    pipeline_id: str
    pipeline_version: str
    kind: JobKind
    state: JobState
    session_id: str
    inputs: dict[str, object] = Field(default_factory=dict)
    parameters: dict[str, object] = Field(default_factory=dict)
    artifacts: list[Artifact] = Field(default_factory=list)
    metrics: JobMetrics = Field(default_factory=JobMetrics)
    failure: AstronomyError | None = None
    provenance: dict[str, object] = Field(default_factory=dict)
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
