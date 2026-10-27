"""Shared device models and enums."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DeviceKind(str, Enum):
    MOUNT = "mount"
    CAMERA = "camera"


class DeviceConnectionState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DEGRADED = "degraded"
    ERROR = "error"


class DeviceHealth(str, Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"


class DeviceImplementation(str, Enum):
    SIMULATOR = "simulator"
    STUB = "stub"
    REAL = "real"


class TrackingMode(str, Enum):
    OFF = "off"
    SIDEREAL = "sidereal"
    LUNAR = "lunar"
    SOLAR = "solar"


class DeviceErrorInfo(BaseModel):
    code: str
    message: str
    recoverable: bool = True


class DeviceCapabilities(BaseModel):
    can_connect: bool = True
    can_disconnect: bool = True
    supports_manual_slew: bool = False
    supports_goto: bool = False
    supports_tracking_mode: bool = False
    supports_preview: bool = False
    supports_still_capture: bool = False
    supports_sequence_capture: bool = False
    notes: list[str] = Field(default_factory=list)


class DeviceStatus(BaseModel):
    device_id: str
    kind: DeviceKind
    name: str
    implementation: DeviceImplementation
    connection_state: DeviceConnectionState
    health: DeviceHealth
    message: str
    capabilities: DeviceCapabilities
    last_seen_at: datetime = Field(default_factory=utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: DeviceErrorInfo | None = None


class MountCoordinates(BaseModel):
    azimuth_deg: float = Field(ge=0, lt=360, allow_inf_nan=False)
    altitude_deg: float = Field(ge=-5, le=90, allow_inf_nan=False)


class CameraRoi(BaseModel):
    x: int = Field(default=0, ge=0)
    y: int = Field(default=0, ge=0)
    width: int | None = Field(default=None, gt=0, le=16384)
    height: int | None = Field(default=None, gt=0, le=16384)


class CameraConfiguration(BaseModel):
    exposure_ms: int = Field(default=50, ge=1, le=60000)
    gain: int = Field(default=100, ge=0, le=65535)
    roi: CameraRoi = Field(default_factory=CameraRoi)
    binning: int = Field(default=1, ge=1, le=4)


class DeviceCommandResult(BaseModel):
    accepted: bool
    message: str
    status: Literal["ok", "rejected", "pending"] = "ok"
    payload: dict[str, Any] = Field(default_factory=dict)


class CapturedFrame(BaseModel):
    format: str
    bytes_payload: bytes
    width: int
    height: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class SimulatedFault(BaseModel):
    mode: Literal["disconnect", "error", "recover"]
    message: str | None = None
