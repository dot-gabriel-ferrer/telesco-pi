"""Player One Mars-M/Mars-C adapter: serialized full-frame single-shot capture."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import ctypes as ct
from pathlib import Path
import re
from typing import TypeVar

import cv2
import numpy as np

from libs.config.settings import Settings
from libs.devices.interfaces import CameraDriver, DeviceOperationError
from libs.devices.models import (
    CameraConfiguration, CapturedFrame, DeviceCapabilities, DeviceCommandResult,
    DeviceConnectionState, DeviceErrorInfo, DeviceHealth, DeviceImplementation,
    DeviceKind, DeviceStatus,
)
from libs.devices.player_one_sdk import CameraProperties, PlayerOneSdk, text

T = TypeVar("T")


class PlayerOneCameraDriver(CameraDriver):
    def __init__(self, settings: Settings, device_id: str = "camera.primary") -> None:
        self.settings = settings
        self.device_id = device_id
        self._sdk: PlayerOneSdk | None = None
        self._camera: CameraProperties | None = None
        self._lock = asyncio.Lock()
        self._error: DeviceErrorInfo | None = None
        self._configuration = CameraConfiguration()
        self._preview_active = False
        self._ranges: dict[int, tuple[int, int]] = {}
        self._width = self._height = 0

    async def _run(self, function: Callable[[], T]) -> T:
        # Cancellation must not release the lock while native SDK code is still
        # accessing the same camera from its worker thread.
        task = asyncio.get_running_loop().run_in_executor(None, function)
        cancelled = False
        while True:
            try:
                result = await asyncio.shield(task)
                break
            except asyncio.CancelledError:
                cancelled = True
        if cancelled:
            raise asyncio.CancelledError
        return result

    def _connected(self) -> tuple[PlayerOneSdk, CameraProperties]:
        if self._sdk is None or self._camera is None:
            raise DeviceOperationError("camera_not_connected", "Player One camera is not connected.")
        if self._error:
            raise DeviceOperationError(self._error.code, self._error.message)
        return self._sdk, self._camera

    def _apply(self, configuration: CameraConfiguration) -> None:
        sdk, camera = self._connected()
        roi = configuration.roi
        if configuration.binning != 1 or roi.x or roi.y or roi.width is not None or roi.height is not None:
            raise DeviceOperationError("player_one_configuration_unsupported", "Player One currently supports full-frame and binning 1 only.")
        requested = {0: configuration.exposure_ms * 1000, 1: configuration.gain}
        for config_id, value in requested.items():
            minimum, maximum = self._ranges[config_id]
            if not minimum <= value <= maximum:
                units = "microseconds" if config_id == 0 else "gain units"
                raise DeviceOperationError("player_one_configuration_range", f"Control {config_id} must be {minimum}–{maximum} {units}.")
        try:
            for config_id, value in requested.items():
                sdk.set_integer(camera.cameraID, config_id, value)
                actual, automatic = sdk.get_integer(camera.cameraID, config_id)
                if actual != value or automatic:
                    raise DeviceOperationError("player_one_readback", f"Camera did not retain requested manual control {config_id}.")
        except DeviceOperationError as exc:
            self._error = DeviceErrorInfo(code=exc.code, message=f"{exc.message} Reconnect before continuing.")
            self._preview_active = False
            raise
        self._configuration = configuration.model_copy(deep=True)

    def _open(self) -> None:
        if self.settings.player_one_sdk_root is None:
            raise DeviceOperationError("player_one_sdk_unavailable", "Set TELESCO_PI_PLAYER_ONE_SDK_ROOT to the extracted official Linux SDK.")
        self._sdk = PlayerOneSdk(Path(self.settings.player_one_sdk_root))
        cameras = self._sdk.enumerate()
        matching = [camera for camera in cameras if re.search(
            r"(?:^|[^a-z0-9])mars[-_ ]?[mc]\s*$", text(camera.cameraModelName).lower(),
        )]
        if self.settings.camera_id is not None:
            matching = [camera for camera in matching if self.settings.camera_id in (
                str(camera.cameraID), text(camera.SN),
            )]
        if len(matching) != 1:
            raise DeviceOperationError("player_one_selection", "Exactly one Mars-M/Mars-C must match. Connect it or set TELESCO_PI_CAMERA_ID to its serial/SDK ID.")
        camera = matching[0]
        if camera.isColorCamera and camera.bayerPattern not in (0, 1, 2, 3):
            raise DeviceOperationError("player_one_bayer", "Color camera returned an unsupported Bayer pattern.")
        image_format = 1 if self.settings.player_one_bit_depth == 16 else 0
        formats = list(camera.imgFormats)
        formats = formats[:formats.index(-1)] if -1 in formats else formats
        if image_format not in formats or 1 not in camera.bins:
            raise DeviceOperationError("player_one_format", "Camera does not support requested RAW format and binning 1.")
        if not (0 < camera.maxWidth * camera.maxHeight <= 16_000_000 and camera.maxWidth > 0 and camera.maxHeight > 0):
            raise DeviceOperationError("player_one_dimensions", "Invalid or unsupported sensor dimensions.")
        self._sdk.call("POAOpenCamera", camera.cameraID)
        self._camera = camera
        self._sdk.call("POAInitCamera", camera.cameraID)
        self._sdk.call("POASetImageBin", camera.cameraID, 1)
        self._sdk.call("POASetImageStartPos", camera.cameraID, 0, 0)
        self._sdk.call("POASetImageSize", camera.cameraID, camera.maxWidth, camera.maxHeight)
        self._width, self._height = self._sdk.size(camera.cameraID)
        if (self._width, self._height) != (camera.maxWidth, camera.maxHeight):
            raise DeviceOperationError("player_one_dimensions", "SDK adjusted full-frame dimensions unexpectedly.")
        self._sdk.call("POASetImageFormat", camera.cameraID, image_format)
        actual_format = ct.c_int()
        self._sdk.call("POAGetImageFormat", camera.cameraID, ct.byref(actual_format))
        if actual_format.value != image_format:
            raise DeviceOperationError("player_one_readback", "Camera did not retain the requested RAW format.")
        for config_id in (0, 1):
            attributes = self._sdk.attributes(camera.cameraID, config_id)
            self._ranges[config_id] = (attributes.minValue.intValue, attributes.maxValue.intValue)
        self._apply(self._configuration)

    def _close(self) -> None:
        sdk, camera = self._sdk, self._camera
        try:
            if sdk is not None and camera is not None:
                stop_error = None
                try:
                    sdk.call("POAStopExposure", camera.cameraID)
                except DeviceOperationError as exc:
                    stop_error = exc
                try:
                    sdk.call("POACloseCamera", camera.cameraID)
                except DeviceOperationError as close_error:
                    if stop_error is not None:
                        raise DeviceOperationError("player_one_cleanup", f"{stop_error.message} Camera close failed: {close_error.message}") from close_error
                    raise
                self._camera = None
                if stop_error is not None:
                    raise stop_error
        finally:
            self._preview_active = False

    async def connect(self) -> DeviceCommandResult:
        async with self._lock:
            if self._camera is not None:
                self._connected()
                return DeviceCommandResult(accepted=True, message="Player One already connected.")
            self._error = None
            try:
                await self._run(self._open)
            except asyncio.CancelledError:
                self._error = DeviceErrorInfo(code="player_one_connect_cancelled", message="Connection cancelled; camera closed. Reconnect explicitly.")
                await self._run(self._close)
                raise
            except DeviceOperationError as exc:
                self._error = DeviceErrorInfo(code=exc.code, message=exc.message)
                try:
                    await self._run(self._close)
                except DeviceOperationError as cleanup:
                    self._error = DeviceErrorInfo(code="player_one_cleanup", message=f"{exc.message} Cleanup failed: {cleanup.message}")
                    raise DeviceOperationError(self._error.code, self._error.message) from cleanup
                raise
        return DeviceCommandResult(accepted=True, message=f"Player One connected; RAW{self.settings.player_one_bit_depth} full-frame. Physical validation pending.")

    async def disconnect(self) -> DeviceCommandResult:
        async with self._lock:
            try:
                await self._run(self._close)
            except DeviceOperationError as exc:
                self._error = DeviceErrorInfo(code=exc.code, message=exc.message)
                raise
            self._error = None
        return DeviceCommandResult(accepted=True, message="Player One camera closed.")

    async def configure(self, configuration: CameraConfiguration) -> DeviceCommandResult:
        async with self._lock:
            await self._run(lambda: self._apply(configuration))
        return DeviceCommandResult(accepted=True, message="Mars-M exposure and gain applied and read back.")

    def _capture(self) -> CapturedFrame:
        sdk, camera = self._connected()
        raw16 = self.settings.player_one_bit_depth == 16
        image = np.empty((self._height, self._width), dtype=np.dtype("<u2") if raw16 else np.uint8)
        try:
            try:
                sdk.call("POAStartExposure", camera.cameraID, 1)
                timeout_ms = self._configuration.exposure_ms + round(self.settings.device_timeout_seconds * 1000)
                sdk.call("POAGetImageData", camera.cameraID, image.ctypes.data_as(ct.c_void_p), image.nbytes, timeout_ms)
            except DeviceOperationError as exposure_error:
                try:
                    sdk.call("POAStopExposure", camera.cameraID)
                except DeviceOperationError as stop_error:
                    raise DeviceOperationError("player_one_cleanup", f"{exposure_error.message} Exposure cleanup failed: {stop_error.message}") from stop_error
                raise
            else:
                sdk.call("POAStopExposure", camera.cameraID)
        except DeviceOperationError as exc:
            self._error = DeviceErrorInfo(code=exc.code, message=exc.message)
            self._preview_active = False
            raise
        ok, encoded = cv2.imencode(".png", image)
        if not ok:
            raise DeviceOperationError("player_one_encode", "Could not encode Player One frame.")
        return CapturedFrame(
            format="png", bytes_payload=encoded.tobytes(), width=self._width, height=self._height,
            metadata={"generated_by": "player_one", "sdk_version": sdk.version,
                      "camera_model": text(camera.cameraModelName), "camera_serial": text(camera.SN),
                      "bit_depth": self.settings.player_one_bit_depth,
                      "sensor_adc_bit_depth": camera.bitDepth, "exposure_ms": self._configuration.exposure_ms,
                      "bayer_pattern": ("RGGB", "BGGR", "GRBG", "GBRG")[camera.bayerPattern] if camera.isColorCamera else None,
                      "gain": self._configuration.gain, "raw": True, "binning": 1},
        )

    async def capture_still(self) -> CapturedFrame:
        async with self._lock:
            return await self._run(self._capture)

    async def start_preview(self) -> DeviceCommandResult:
        async with self._lock:
            self._connected()
            self._preview_active = True
        return DeviceCommandResult(accepted=True, message="Player One preview enabled (single-shot polling, not high-speed video).")

    async def stop_preview(self) -> DeviceCommandResult:
        async with self._lock:
            self._preview_active = False
        return DeviceCommandResult(accepted=True, message="Player One preview disabled.")

    async def get_status(self) -> DeviceStatus:
        return DeviceStatus(
            device_id=self.device_id, kind=DeviceKind.CAMERA,
            name=text(self._camera.cameraModelName) if self._camera else "Player One Mars-M / Mars-C",
            implementation=DeviceImplementation.REAL,
            connection_state=DeviceConnectionState.ERROR if self._error else (
                DeviceConnectionState.CONNECTED if self._camera is not None else DeviceConnectionState.DISCONNECTED),
            health=DeviceHealth.ERROR if self._error else DeviceHealth.WARNING,
            message=self._error.message if self._error else "Native Player One SDK adapter; physical validation pending.",
            capabilities=DeviceCapabilities(
                supports_preview=True, supports_still_capture=True,
                notes=["Full-frame RAW8/RAW16 PNG; binning 1; preview via single shots. No sequence/video support yet."],
            ),
            metadata={"configuration": self._configuration.model_dump(), "preview_active": self._preview_active,
                      "sdk_version": self._sdk.version if self._sdk else None, "hardware_validation": "pending",
                      "camera_model": text(self._camera.cameraModelName) if self._camera else None,
                      "camera_serial": text(self._camera.SN) if self._camera else None,
                      "bit_depth": self.settings.player_one_bit_depth, "width": self._width, "height": self._height,
                      "control_ranges": {str(key): list(value) for key, value in self._ranges.items()}},
            error=self._error,
        )
