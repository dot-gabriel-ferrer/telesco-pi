"""Hardware validation stubs for unsupported real integrations."""

from __future__ import annotations

from libs.devices.interfaces import CameraDriver, DeviceOperationError, MountDriver
from libs.devices.models import (
    CameraConfiguration,
    CapturedFrame,
    DeviceCapabilities,
    DeviceCommandResult,
    DeviceConnectionState,
    DeviceHealth,
    DeviceImplementation,
    DeviceStatus,
    DeviceKind,
    MountCoordinates,
    TrackingMode,
)


class _StubBase:
    implementation = DeviceImplementation.STUB

    def _unsupported(self, reason: str) -> DeviceCommandResult:
        return DeviceCommandResult(
            accepted=False,
            status="rejected",
            message=reason,
            payload={"integration_state": "pending_hardware_validation"},
        )


class AZGo2MountDriverStub(_StubBase, MountDriver):
    def __init__(self, device_id: str = "mount.primary") -> None:
        self.device_id = device_id

    async def connect(self) -> DeviceCommandResult:
        return self._unsupported("AZ-Go2 direct protocol support is pending real-device validation.")

    async def disconnect(self) -> DeviceCommandResult:
        return DeviceCommandResult(accepted=True, status="ok", message="Stub disconnected.")

    async def get_status(self) -> DeviceStatus:
        return DeviceStatus(
            device_id=self.device_id,
            kind=DeviceKind.MOUNT,
            name="SkyWatcher AZ-Go2",
            implementation=self.implementation,
            connection_state=DeviceConnectionState.DISCONNECTED,
            health=DeviceHealth.WARNING,
            message="Real mount integration is stubbed pending protocol validation.",
            capabilities=DeviceCapabilities(
                supports_manual_slew=True,
                supports_goto=True,
                supports_tracking_mode=True,
                notes=[
                    "Stub only.",
                    "Pending validation of direct Linux control path or fallback to INDI.",
                ],
            ),
            metadata={"hardware_validation": "pending"},
        )

    async def manual_slew(self, delta_azimuth: float, delta_altitude: float) -> DeviceCommandResult:
        return self._unsupported("Manual slew is unavailable in the mount stub.")

    async def goto(self, coordinates: MountCoordinates) -> DeviceCommandResult:
        return self._unsupported("Goto is unavailable in the mount stub.")

    async def stop(self) -> DeviceCommandResult:
        return self._unsupported("Stop is unavailable in the mount stub.")

    async def set_tracking_mode(self, mode: TrackingMode) -> DeviceCommandResult:
        return self._unsupported("Tracking mode is unavailable in the mount stub.")


class PlayerOneMarsMCameraDriverStub(_StubBase, CameraDriver):
    def __init__(self, device_id: str = "camera.primary") -> None:
        self.device_id = device_id

    async def connect(self) -> DeviceCommandResult:
        return self._unsupported("Player One Mars M Linux ARM64 SDK validation is pending.")

    async def disconnect(self) -> DeviceCommandResult:
        return DeviceCommandResult(accepted=True, status="ok", message="Stub disconnected.")

    async def get_status(self) -> DeviceStatus:
        return DeviceStatus(
            device_id=self.device_id,
            kind=DeviceKind.CAMERA,
            name="Player One Mars M",
            implementation=self.implementation,
            connection_state=DeviceConnectionState.DISCONNECTED,
            health=DeviceHealth.WARNING,
            message="Real camera integration is stubbed pending SDK validation.",
            capabilities=DeviceCapabilities(
                supports_preview=True,
                supports_still_capture=True,
                supports_sequence_capture=True,
                notes=[
                    "Stub only.",
                    "Pending validation of vendor SDK availability on Raspberry Pi OS 64-bit.",
                ],
            ),
            metadata={"hardware_validation": "pending"},
        )

    async def configure(self, configuration: CameraConfiguration) -> DeviceCommandResult:
        return self._unsupported("Camera configuration is unavailable in the camera stub.")

    async def capture_still(self) -> CapturedFrame:
        raise DeviceOperationError(
            code="camera_stub_unavailable",
            message="Still capture is unavailable in the camera stub.",
        )

    async def start_preview(self) -> DeviceCommandResult:
        return self._unsupported("Preview is unavailable in the camera stub.")

    async def stop_preview(self) -> DeviceCommandResult:
        return self._unsupported("Preview is unavailable in the camera stub.")
