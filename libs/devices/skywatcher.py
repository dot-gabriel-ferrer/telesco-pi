"""Independent, bounded motor-controller integration over SkyWatcher WiFi."""

from __future__ import annotations

import asyncio
import math
import socket

from libs.config.settings import Settings
from libs.devices.interfaces import DeviceOperationError, MountDriver
from libs.devices.models import (
    DeviceCapabilities, DeviceCommandResult, DeviceConnectionState, DeviceErrorInfo,
    DeviceHealth, DeviceImplementation, DeviceKind, DeviceStatus, MountCoordinates,
    TrackingMode,
)


def encode_u24(value: int) -> str:
    if not 0 <= value <= 0xFFFFFF:
        raise DeviceOperationError("mount_range", "Motor value exceeds the 24-bit protocol range.")
    return value.to_bytes(3, "little").hex().upper()


def decode_u24(payload: str) -> int:
    try:
        if len(payload) != 6:
            raise ValueError("Expected three bytes.")
        data = bytes.fromhex(payload)
        if len(data) != 3:
            raise ValueError("Expected three bytes.")
        return int.from_bytes(data, "little")
    except ValueError as exc:
        raise DeviceOperationError("mount_protocol", "Invalid motor-controller response.") from exc


class SkyWatcherUdpMountDriver(MountDriver):
    """Relative steps only: absolute pointing requires a calibrated reference."""

    def __init__(self, settings: Settings, device_id: str = "mount.primary") -> None:
        self.device_id = device_id
        self.settings = settings
        self._socket: socket.socket | None = None
        self._lock = asyncio.Lock()
        self._steps: dict[int, int] = {}
        self._timers: dict[int, int] = {}
        self._error: DeviceErrorInfo | None = None

    async def _command(self, command: str, axis: int, data: str = "") -> str:
        if self._socket is None:
            raise DeviceOperationError("mount_not_connected", "Mount is not connected.")
        loop = asyncio.get_running_loop()
        try:
            await loop.sock_sendall(self._socket, f":{command}{axis}{data}\r".encode("ascii"))
            reply = await asyncio.wait_for(
                loop.sock_recv(self._socket, 128), self.settings.device_timeout_seconds,
            )
        except (OSError, TimeoutError) as exc:
            self._error = DeviceErrorInfo(code="mount_transport", message="Mount link lost; motion state is unknown. Reconnect and check the mount.")
            # UDP has no request identifiers. Discard the socket after timeout so a
            # late acknowledgement cannot be mistaken for the next command.
            self._socket.close()
            self._socket = None
            raise DeviceOperationError(self._error.code, self._error.message) from exc
        try:
            text = reply.decode("ascii")
        except UnicodeDecodeError as exc:
            raise DeviceOperationError("mount_protocol", "Non-ASCII mount response.") from exc
        if text.startswith("!"):
            raise DeviceOperationError("mount_rejected", f"Motor controller rejected command {command}{axis}: {text.strip()}")
        if not text.startswith("=") or not text.endswith("\r"):
            raise DeviceOperationError("mount_protocol", "Malformed motor-controller response.")
        return text[1:-1]

    async def connect(self) -> DeviceCommandResult:
        async with self._lock:
            if self._socket is not None:
                return DeviceCommandResult(accepted=True, message="Mount already connected.")
            loop = asyncio.get_running_loop()
            try:
                addresses = await asyncio.wait_for(loop.getaddrinfo(
                    self.settings.mount_host, self.settings.mount_port,
                    family=socket.AF_INET, type=socket.SOCK_DGRAM,
                ), self.settings.device_timeout_seconds)
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self._socket.setblocking(False)
                await loop.sock_connect(self._socket, addresses[0][4])
                for axis in (1, 2):
                    decode_u24(await self._command("e", axis))
                    self._steps[axis] = decode_u24(await self._command("a", axis))
                    self._timers[axis] = decode_u24(await self._command("b", axis))
                    if not self._steps[axis] or not self._timers[axis]:
                        raise DeviceOperationError("mount_protocol", "Controller reported zero gear/timer constants.")
                self._error = None
            except (OSError, DeviceOperationError) as exc:
                if self._socket is not None:
                    self._socket.close()
                    self._socket = None
                error = exc if isinstance(exc, DeviceOperationError) else DeviceOperationError("mount_transport", str(exc))
                self._error = DeviceErrorInfo(code=error.code, message=error.message)
                raise error from exc
        return DeviceCommandResult(accepted=True, message="SkyWatcher controller connected; physical validation pending.")

    async def _stop_axes(self) -> None:
        errors: list[DeviceOperationError] = []
        for axis in (1, 2):
            try:
                await self._command("K", axis)
            except DeviceOperationError as exc:
                errors.append(exc)
        if errors:
            raise errors[0]

    async def disconnect(self) -> DeviceCommandResult:
        async with self._lock:
            try:
                if self._socket is not None:
                    await self._stop_axes()
            finally:
                if self._socket is not None:
                    self._socket.close()
                    self._socket = None
        return DeviceCommandResult(accepted=True, message="Mount stopped and disconnected.")

    async def get_status(self) -> DeviceStatus:
        return DeviceStatus(
            device_id=self.device_id, kind=DeviceKind.MOUNT, name="SkyWatcher UDP",
            implementation=DeviceImplementation.REAL,
            connection_state=DeviceConnectionState.ERROR if self._error else (
                DeviceConnectionState.CONNECTED if self._socket else DeviceConnectionState.DISCONNECTED
            ),
            health=DeviceHealth.ERROR if self._error else DeviceHealth.WARNING,
            message=self._error.message if self._error else "Relative motor control; hardware validation pending.",
            capabilities=DeviceCapabilities(
                supports_manual_slew=self.settings.mount_motion_enabled,
                notes=["Physical motion requires explicit enablement. Bounded relative moves only. No absolute GoTo, PARK or uncalibrated alt-az tracking."],
            ),
            metadata={"host": self.settings.mount_host, "port": self.settings.mount_port,
                      "motion_enabled": self.settings.mount_motion_enabled,
                      "max_step_deg": self.settings.mount_max_step_deg, "hardware_validation": "pending"},
            error=self._error,
        )

    async def manual_slew(self, delta_azimuth: float, delta_altitude: float) -> DeviceCommandResult:
        if not self.settings.mount_motion_enabled:
            raise DeviceOperationError("mount_motion_disabled", "Physical movement is disabled. An on-site operator must authorize the test before enabling it.")
        if any(not math.isfinite(delta) or abs(delta) > self.settings.mount_max_step_deg
               for delta in (delta_azimuth, delta_altitude)):
            raise DeviceOperationError("mount_range", "Requested step exceeds the configured manual movement limit.")
        async with self._lock:
            if self._socket is None:
                raise DeviceOperationError("mount_not_connected", "Mount is not connected.")
            # Do not replace a moving command or change direction while an axis runs.
            for axis in (1, 2):
                status = await self._command("f", axis)
                if len(status) != 6 or any(c not in "0123456789abcdefABCDEF" for c in status):
                    raise DeviceOperationError("mount_protocol", "Invalid motor status.")
                if int(status[2:4], 16) & 1:
                    raise DeviceOperationError("mount_busy", "An axis is moving. Wait or press STOP.")
            try:
                for axis, delta in ((1, delta_azimuth), (2, delta_altitude)):
                    steps = round(abs(delta) * self._steps[axis] / 360)
                    if not steps:
                        continue
                    # Low-speed finite goto, not continuous slewing. Timer limits
                    # speed to at most 0.25 degrees/s, independently of the UI.
                    period = math.ceil(self._timers[axis] * 360 / (self._steps[axis] * 0.25))
                    await self._command("F", axis)
                    await self._command("G", axis, "20" if delta > 0 else "21")
                    await self._command("I", axis, encode_u24(max(6, period)))
                    await self._command("H", axis, encode_u24(steps))
                    await self._command("M", axis, encode_u24(min(steps, max(1, steps // 10))))
                    await self._command("J", axis)
            except DeviceOperationError:
                if self._socket is not None:
                    await self._stop_axes()
                raise
        return DeviceCommandResult(accepted=True, status="pending", message="Bounded relative move submitted.")

    async def stop(self) -> DeviceCommandResult:
        async with self._lock:
            await self._stop_axes()
        return DeviceCommandResult(accepted=True, message="STOP acknowledged by both axes.")

    async def goto(self, coordinates: MountCoordinates) -> DeviceCommandResult:
        raise DeviceOperationError("mount_reference_required", "Absolute GoTo is disabled until a calibrated reference is implemented.")

    async def set_tracking_mode(self, mode: TrackingMode) -> DeviceCommandResult:
        if mode == TrackingMode.OFF:
            return await self.stop()
        raise DeviceOperationError("mount_reference_required", "Alt-az tracking requires a calibrated closed-loop controller.")
