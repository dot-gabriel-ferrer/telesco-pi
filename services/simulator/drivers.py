"""First-level simulator drivers."""

from __future__ import annotations

import asyncio
import math
from datetime import datetime, timezone

from libs.config.settings import Settings
from libs.devices.interfaces import CameraDriver, DeviceOperationError, MountDriver
from libs.devices.models import (
    CameraConfiguration,
    CapturedFrame,
    DeviceCapabilities,
    DeviceCommandResult,
    DeviceConnectionState,
    DeviceHealth,
    DeviceImplementation,
    DeviceKind,
    DeviceStatus,
    MountCoordinates,
    SimulatedFault,
    TrackingMode,
)


class SimulatedMountDriver(MountDriver):
    """Mount simulator with explicit state transitions."""

    def __init__(self, settings: Settings, device_id: str = "mount.primary") -> None:
        self.settings = settings
        self.device_id = device_id
        self._connection_state = DeviceConnectionState.DISCONNECTED
        self._health = DeviceHealth.HEALTHY
        self._message = "Mount simulator idle."
        self._tracking_mode = TrackingMode.OFF
        self._coordinates = MountCoordinates(azimuth_deg=180.0, altitude_deg=45.0)
        self._fault: SimulatedFault | None = None
        self._goto_task: asyncio.Task | None = None

    async def connect(self) -> DeviceCommandResult:
        self._connection_state = DeviceConnectionState.CONNECTED
        self._health = DeviceHealth.HEALTHY
        self._message = "Mount simulator connected."
        return DeviceCommandResult(accepted=True, message=self._message)

    async def disconnect(self) -> DeviceCommandResult:
        if self._goto_task:
            self._goto_task.cancel()
            self._goto_task = None
        self._connection_state = DeviceConnectionState.DISCONNECTED
        self._message = "Mount simulator disconnected."
        return DeviceCommandResult(accepted=True, message=self._message)

    async def get_status(self) -> DeviceStatus:
        return DeviceStatus(
            device_id=self.device_id,
            kind=DeviceKind.MOUNT,
            name="Simulated Mount",
            implementation=DeviceImplementation.SIMULATOR,
            connection_state=self._connection_state,
            health=self._health,
            message=self._message,
            capabilities=DeviceCapabilities(
                supports_manual_slew=True,
                supports_goto=True,
                supports_tracking_mode=True,
                notes=["Synthetic az/alt state machine.", "Supports fault injection for disconnect/error."],
            ),
            metadata={
                "coordinates": self._coordinates.model_dump(),
                "tracking_mode": self._tracking_mode.value,
                "fault": self._fault.model_dump() if self._fault else None,
            },
        )

    def _ensure_connected(self) -> None:
        if self._fault and self._fault.mode == "error":
            raise DeviceOperationError("simulated_mount_error", self._fault.message or "Injected mount fault.")
        if self._fault and self._fault.mode == "disconnect":
            raise DeviceOperationError("simulated_mount_disconnect", "Simulated mount disconnection.")
        if self._connection_state != DeviceConnectionState.CONNECTED:
            raise DeviceOperationError("mount_not_connected", "Mount is not connected.")

    async def manual_slew(self, delta_azimuth: float, delta_altitude: float) -> DeviceCommandResult:
        self._ensure_connected()
        self._coordinates.azimuth_deg = (self._coordinates.azimuth_deg + delta_azimuth) % 360
        self._coordinates.altitude_deg = max(-5.0, min(90.0, self._coordinates.altitude_deg + delta_altitude))
        self._message = "Mount slewed manually."
        return DeviceCommandResult(accepted=True, message=self._message, payload=self._coordinates.model_dump())

    async def goto(self, coordinates: MountCoordinates) -> DeviceCommandResult:
        self._ensure_connected()
        if self._goto_task:
            self._goto_task.cancel()

        async def _move() -> None:
            await asyncio.sleep(0.2)
            self._coordinates = coordinates
            self._message = "Mount goto completed."

        self._message = "Mount goto in progress."
        self._goto_task = asyncio.create_task(_move())
        return DeviceCommandResult(accepted=True, status="pending", message=self._message)

    async def stop(self) -> DeviceCommandResult:
        if self._goto_task:
            self._goto_task.cancel()
            self._goto_task = None
        self._message = "Mount motion stopped."
        return DeviceCommandResult(accepted=True, message=self._message)

    async def set_tracking_mode(self, mode: TrackingMode) -> DeviceCommandResult:
        self._ensure_connected()
        self._tracking_mode = mode
        self._message = f"Tracking mode set to {mode.value}."
        return DeviceCommandResult(accepted=True, message=self._message, payload={"tracking_mode": mode.value})

    async def inject_fault(self, fault: SimulatedFault | None) -> DeviceCommandResult:
        self._fault = fault
        if fault is None or fault.mode == "recover":
            self._fault = None
            self._health = DeviceHealth.HEALTHY
            if self._connection_state in {DeviceConnectionState.ERROR, DeviceConnectionState.DEGRADED}:
                self._connection_state = DeviceConnectionState.CONNECTED
            self._message = "Mount simulator recovered."
        elif fault.mode == "disconnect":
            self._connection_state = DeviceConnectionState.DEGRADED
            self._health = DeviceHealth.WARNING
            self._message = fault.message or "Mount simulator disconnected by fault injection."
        else:
            self._connection_state = DeviceConnectionState.ERROR
            self._health = DeviceHealth.ERROR
            self._message = fault.message or "Mount simulator error injected."
        return DeviceCommandResult(accepted=True, message=self._message)


class SimulatedCameraDriver(CameraDriver):
    """Camera simulator that writes grayscale PGM frames."""

    def __init__(self, settings: Settings, device_id: str = "camera.primary") -> None:
        self.settings = settings
        self.device_id = device_id
        self._connection_state = DeviceConnectionState.DISCONNECTED
        self._health = DeviceHealth.HEALTHY
        self._message = "Camera simulator idle."
        self._fault: SimulatedFault | None = None
        self._configuration = CameraConfiguration(
            roi={"width": settings.simulation_frame_width, "height": settings.simulation_frame_height}
        )
        self._preview_active = False

    async def connect(self) -> DeviceCommandResult:
        self._connection_state = DeviceConnectionState.CONNECTED
        self._health = DeviceHealth.HEALTHY
        self._message = "Camera simulator connected."
        return DeviceCommandResult(accepted=True, message=self._message)

    async def disconnect(self) -> DeviceCommandResult:
        self._connection_state = DeviceConnectionState.DISCONNECTED
        self._preview_active = False
        self._message = "Camera simulator disconnected."
        return DeviceCommandResult(accepted=True, message=self._message)

    async def get_status(self) -> DeviceStatus:
        return DeviceStatus(
            device_id=self.device_id,
            kind=DeviceKind.CAMERA,
            name="Simulated Camera",
            implementation=DeviceImplementation.SIMULATOR,
            connection_state=self._connection_state,
            health=self._health,
            message=self._message,
            capabilities=DeviceCapabilities(
                supports_preview=True,
                supports_still_capture=True,
                supports_sequence_capture=True,
                notes=["Grayscale synthetic PGM frames.", "Supports fault injection for disconnect/error."],
            ),
            metadata={
                "configuration": self._configuration.model_dump(),
                "preview_active": self._preview_active,
                "fault": self._fault.model_dump() if self._fault else None,
            },
        )

    def _ensure_connected(self) -> None:
        if self._fault and self._fault.mode == "error":
            raise DeviceOperationError("simulated_camera_error", self._fault.message or "Injected camera fault.")
        if self._fault and self._fault.mode == "disconnect":
            raise DeviceOperationError("simulated_camera_disconnect", "Simulated camera disconnection.")
        if self._connection_state != DeviceConnectionState.CONNECTED:
            raise DeviceOperationError("camera_not_connected", "Camera is not connected.")

    async def configure(self, configuration: CameraConfiguration) -> DeviceCommandResult:
        self._ensure_connected()
        self._configuration = configuration
        self._message = "Camera simulator configured."
        return DeviceCommandResult(accepted=True, message=self._message)

    async def capture_still(self) -> CapturedFrame:
        self._ensure_connected()
        width = self._configuration.roi.width or self.settings.simulation_frame_width
        height = self._configuration.roi.height or self.settings.simulation_frame_height
        header = f"P5\n{width} {height}\n255\n".encode("ascii")
        body = bytearray()
        timestamp = datetime.now(timezone.utc).timestamp()
        for y in range(height):
            for x in range(width):
                value = int(
                    (
                        128
                        + 64 * math.sin(x / 21.0)
                        + 48 * math.cos(y / 31.0)
                        + 15 * math.sin(timestamp + (x + y) / 70.0)
                    )
                )
                body.append(max(0, min(255, value)))
        payload = header + bytes(body)
        self._message = "Still capture complete."
        return CapturedFrame(
            format="pgm",
            bytes_payload=payload,
            width=width,
            height=height,
            metadata={
                "exposure_ms": self._configuration.exposure_ms,
                "gain": self._configuration.gain,
                "generated_by": "simulated_camera",
            },
        )

    async def start_preview(self) -> DeviceCommandResult:
        self._ensure_connected()
        self._preview_active = True
        self._message = "Camera preview started."
        return DeviceCommandResult(accepted=True, message=self._message)

    async def stop_preview(self) -> DeviceCommandResult:
        self._preview_active = False
        self._message = "Camera preview stopped."
        return DeviceCommandResult(accepted=True, message=self._message)

    async def inject_fault(self, fault: SimulatedFault | None) -> DeviceCommandResult:
        self._fault = fault
        if fault is None or fault.mode == "recover":
            self._fault = None
            self._health = DeviceHealth.HEALTHY
            if self._connection_state in {DeviceConnectionState.ERROR, DeviceConnectionState.DEGRADED}:
                self._connection_state = DeviceConnectionState.CONNECTED
            self._message = "Camera simulator recovered."
        elif fault.mode == "disconnect":
            self._health = DeviceHealth.WARNING
            self._connection_state = DeviceConnectionState.DEGRADED
            self._message = fault.message or "Camera simulator disconnected by fault injection."
        else:
            self._health = DeviceHealth.ERROR
            self._connection_state = DeviceConnectionState.ERROR
            self._message = fault.message or "Camera simulator error injected."
        return DeviceCommandResult(accepted=True, message=self._message)

