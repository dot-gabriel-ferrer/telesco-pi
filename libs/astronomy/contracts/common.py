"""Shared contract primitives, envelopes, profiles, and error metadata."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class QualityProfile(str, Enum):
    LOW = 'low'
    BALANCED = 'balanced'
    HIGH = 'high'


class DataSource(str, Enum):
    SIMULATOR = 'simulator'
    REAL = 'real'
    HYBRID = 'hybrid'


class JobKind(str, Enum):
    PLANNER = 'planner'
    SOLVING = 'solving'
    PLANETARY = 'planetary'
    LIVESTACK = 'livestack'
    ORBITAL = 'orbital'
    CALIBRATION = 'calibration'


class JobState(str, Enum):
    QUEUED = 'queued'
    RUNNING = 'running'
    PAUSED = 'paused'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class RequestEnvelope(BaseModel):
    request_id: str
    session_id: str
    contract_version: str = '1.0'
    created_at_utc: datetime = Field(default_factory=utcnow)
    profile: QualityProfile = QualityProfile.BALANCED
    source: DataSource = DataSource.SIMULATOR


class AstronomyError(BaseModel):
    code: str
    message: str
    recoverable: bool = True
    details: dict[str, Any] = Field(default_factory=dict)


class ScientificClaim(BaseModel):
    value: str
    confidence: Literal['verified', 'plausible', 'pending_validation'] = 'pending_validation'
    notes: str | None = None


class TimeBudget(BaseModel):
    timeout_s: int = Field(default=60, ge=1)
    max_memory_mb: int = Field(default=512, ge=32)


class ResourceMetrics(BaseModel):
    runtime_ms: float = 0.0
    peak_mem_mb: float = 0.0
    frames_in: int = 0
    frames_used: int = 0
