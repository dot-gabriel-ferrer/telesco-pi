"""Scientific diagnostics and validation-state markers."""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class ValidationStatus(str, Enum):
    VERIFIED = 'verified'
    PLAUSIBLE = 'plausible'
    PENDING_HARDWARE = 'pending_hardware'


class ScientificDiagnostic(BaseModel):
    name: str
    status: ValidationStatus
    details: str
    limitations: list[str] = Field(default_factory=list)
