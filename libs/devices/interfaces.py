"""Device driver interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod

from libs.devices.models import (
    CameraConfiguration,
    CapturedFrame,
    DeviceCommandResult,
    DeviceStatus,
    MountCoordinates,
    SimulatedFault,
    TrackingMode,
)


class DeviceOperationError(RuntimeError):
    """Raised when a driver operation fails."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class BaseDriver(ABC):
    device_id: str

    @abstractmethod
    async def connect(self) -> DeviceCommandResult:
        raise NotImplementedError

    @abstractmethod
    async def disconnect(self) -> DeviceCommandResult:
        raise NotImplementedError

    @abstractmethod
    async def get_status(self) -> DeviceStatus:
        raise NotImplementedError

    async def inject_fault(self, fault: SimulatedFault | None) -> DeviceCommandResult:
        return DeviceCommandResult(
            accepted=False,
            status="rejected",
            message="Fault injection is not supported by this driver.",
        )


class MountDriver(BaseDriver, ABC):
    @abstractmethod
    async def manual_slew(self, delta_azimuth: float, delta_altitude: float) -> DeviceCommandResult:
        raise NotImplementedError

    @abstractmethod
    async def goto(self, coordinates: MountCoordinates) -> DeviceCommandResult:
        raise NotImplementedError

    @abstractmethod
    async def stop(self) -> DeviceCommandResult:
        raise NotImplementedError

    @abstractmethod
    async def set_tracking_mode(self, mode: TrackingMode) -> DeviceCommandResult:
        raise NotImplementedError


class CameraDriver(BaseDriver, ABC):
    @abstractmethod
    async def configure(self, configuration: CameraConfiguration) -> DeviceCommandResult:
        raise NotImplementedError

    @abstractmethod
    async def capture_still(self) -> CapturedFrame:
        raise NotImplementedError

    @abstractmethod
    async def start_preview(self) -> DeviceCommandResult:
        raise NotImplementedError

    @abstractmethod
    async def stop_preview(self) -> DeviceCommandResult:
        raise NotImplementedError

