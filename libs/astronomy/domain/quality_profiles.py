"""Resource and quality profiles tuned for Raspberry Pi deployments."""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel


class QualityProfile(str, Enum):
    LOW = 'low'
    BALANCED = 'balanced'
    HIGH = 'high'


class ResourceBudget(BaseModel):
    cpu_time_s: int
    max_memory_mb: int
    max_frames_in_memory: int
