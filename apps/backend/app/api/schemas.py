"""API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from libs.devices.models import CameraConfiguration, DeviceStatus, MountCoordinates, SimulatedFault, TrackingMode
from libs.sessions.models import SessionSummary
from libs.storage.models import IndexedFile


class ApiErrorResponse(BaseModel):
    error: str
    code: str
    request_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    timestamp: datetime
    details: dict[str, Any] = Field(default_factory=dict)


class EventEnvelope(BaseModel):
    event_type: str
    source: str
    timestamp: datetime
    correlation_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class NotificationResponse(BaseModel):
    severity: Literal["info", "warning", "error"]
    message: str
    created_at: datetime


class StorageSummaryResponse(BaseModel):
    root_dir: str
    retention_days: int
    indexed_files: int


class SystemStatusResponse(BaseModel):
    app_name: str
    version: str
    environment: str
    status: Literal["ready", "degraded"]
    active_session: SessionSummary | None = None
    devices: list[DeviceStatus] = Field(default_factory=list)
    storage: StorageSummaryResponse
    recent_events: list[EventEnvelope] = Field(default_factory=list)


class SessionCreateRequest(BaseModel):
    name: str
    mode: Literal["simulator", "real", "hybrid"] = "simulator"
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionListResponse(BaseModel):
    items: list[SessionSummary]


class SessionOpenResponse(BaseModel):
    session: SessionSummary


class FileListResponse(BaseModel):
    items: list[IndexedFile]


class DeviceListResponse(BaseModel):
    items: list[DeviceStatus]


class MountManualSlewRequest(BaseModel):
    delta_azimuth: float
    delta_altitude: float


class MountGotoRequest(BaseModel):
    coordinates: MountCoordinates


class MountTrackingRequest(BaseModel):
    mode: TrackingMode


class DeviceFaultRequest(BaseModel):
    fault: SimulatedFault


class CameraConfigureRequest(BaseModel):
    configuration: CameraConfiguration


class CaptureRequest(BaseModel):
    session_id: str | None = None
    name_prefix: str = "capture"


class CaptureResponse(BaseModel):
    status: Literal["ok", "rejected"]
    message: str
    file: IndexedFile | None = None
    preview: IndexedFile | None = None


class PlannerRequest(BaseModel):
    target: str
    session_id: str | None = None
    constraints: dict[str, Any] = Field(default_factory=dict)


class PlannerResponse(BaseModel):
    status: Literal["stub", "ok"]
    message: str
    items: list[dict[str, Any]] = Field(default_factory=list)


class OrbitalRequest(BaseModel):
    object_id: str
    session_id: str | None = None
    constraints: dict[str, Any] = Field(default_factory=dict)


class OrbitalResponse(BaseModel):
    status: Literal["stub", "ok"]
    message: str
    passes: list[dict[str, Any]] = Field(default_factory=list)

