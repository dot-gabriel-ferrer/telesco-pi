"""Headless adapter for an externally installed, authorized Photsat/Nncam SDK."""

from __future__ import annotations

import asyncio
import ctypes
import importlib
import threading
from collections.abc import Callable
from typing import Protocol, cast

import cv2
import numpy as np

from libs.config.settings import Settings
from libs.devices.interfaces import CameraDriver, DeviceOperationError
from libs.devices.models import (
    CameraConfiguration, CapturedFrame, DeviceCapabilities, DeviceCommandResult,
    DeviceConnectionState, DeviceErrorInfo, DeviceHealth, DeviceImplementation,
    DeviceKind, DeviceStatus,
)


class NncamHandle(Protocol):
    def get_Size(self) -> tuple[int, int]: ...
    def get_ExpTimeRange(self) -> tuple[int, int, int]: ...
    def get_ExpoAGainRange(self) -> tuple[int, int, int]: ...
    def put_AutoExpoEnable(self, value: int) -> None: ...
    def put_ExpoTime(self, value: int) -> None: ...
    def put_ExpoAGain(self, value: int) -> None: ...
    def put_Option(self, option: int, value: int) -> None: ...
    def StartPullModeWithCallback(self, callback: Callable[[int, object], None], context: object) -> None: ...
    def PullImageV4(self, buffer: object, still: int, bits: int, pitch: int, info: object) -> None: ...
    def Stop(self) -> None: ...
    def Close(self) -> None: ...


class NncamDevice(Protocol):
    id: str
    displayname: str


class NncamFactory(Protocol):
    def EnumV2(self) -> list[NncamDevice]: ...
    def Open(self, camera_id: str) -> NncamHandle | None: ...


class NncamSdk(Protocol):
    Nncam: NncamFactory
    HRESULTException: type[Exception]
    NNCAM_OPTION_RAW: int
    NNCAM_OPTION_BITDEPTH: int
    NNCAM_EVENT_IMAGE: int
    NNCAM_EVENT_ERROR: int
    NNCAM_EVENT_DISCONNECTED: int


class NncamCameraDriver(CameraDriver):
    def __init__(self, settings: Settings, device_id: str = "camera.primary") -> None:
        self.device_id = device_id
        self.settings = settings
        self._sdk: NncamSdk | None = None
        self._handle: NncamHandle | None = None
        self._sdk_errors: tuple[type[Exception], ...] = (OSError,)
        self._lock = asyncio.Lock()
        self._condition = threading.Condition()
        self._error: DeviceErrorInfo | None = None
        self._frame: bytes | None = None
        self._generation = 0
        self._width = self._height = 0
        self._name = "EHD / Nncam (Photsat)"
        self._configuration = CameraConfiguration()
        self._preview_active = False

    def _connected(self) -> NncamHandle:
        if self._error:
            raise DeviceOperationError(self._error.code, self._error.message)
        if self._handle is None:
            raise DeviceOperationError("camera_not_connected", "Camera is not connected.")
        return self._handle

    def _callback(self, event: int, context: object) -> None:
        sdk, handle = self._sdk, self._handle
        if sdk is None or handle is None:
            return
        with self._condition:
            if event in (sdk.NNCAM_EVENT_ERROR, sdk.NNCAM_EVENT_DISCONNECTED):
                self._error = DeviceErrorInfo(code="camera_link_lost", message="Nncam reported a camera error or disconnection. Disconnect and reconnect.")
            elif event == sdk.NNCAM_EVENT_IMAGE:
                stride = ((self._width + 3) // 4) * 4
                buffer = ctypes.create_string_buffer(stride * self._height)
                try:
                    handle.PullImageV4(buffer, 0, 8, stride, None)
                except self._sdk_errors as exc:
                    self._error = DeviceErrorInfo(code="camera_sdk_error", message=f"Nncam frame read failed: {exc}")
                else:
                    self._frame = buffer.raw
                    self._generation += 1
            self._condition.notify_all()

    def _apply_configuration(self, configuration: CameraConfiguration) -> None:
        handle = self._connected()
        roi = configuration.roi
        if configuration.binning != 1 or roi.x or roi.y or roi.width is not None or roi.height is not None:
            raise DeviceOperationError("camera_configuration_unsupported", "This Nncam adapter currently supports full-frame, binning 1 only.")
        minimum, maximum, _ = handle.get_ExpTimeRange()
        gain_min, gain_max, _ = handle.get_ExpoAGainRange()
        if not minimum <= configuration.exposure_ms * 1000 <= maximum or not gain_min <= configuration.gain <= gain_max:
            raise DeviceOperationError("camera_configuration_range", f"Exposure must be {minimum / 1000:g}–{maximum / 1000:g} ms; gain {gain_min}–{gain_max}.")
        handle.put_AutoExpoEnable(0)
        handle.put_ExpoTime(configuration.exposure_ms * 1000)
        handle.put_ExpoAGain(configuration.gain)
        self._configuration = configuration.model_copy(deep=True)

    def _open(self) -> None:
        try:
            self._sdk = cast(NncamSdk, importlib.import_module(self.settings.camera_sdk_module))
        except (ImportError, OSError) as exc:
            raise DeviceOperationError(
                "camera_sdk_unavailable",
                "Install the authorized Nncam Python module and matching native library (ARM64 on Pi). Player One cameras need their own SDK.",
            ) from exc
        sdk = self._sdk
        self._sdk_errors = (OSError, sdk.HRESULTException)
        try:
            devices = sdk.Nncam.EnumV2()
            selected = next((device for device in devices if device.id == self.settings.camera_id), None) if self.settings.camera_id else (
                devices[0] if len(devices) == 1 else None
            )
            if selected is None:
                raise DeviceOperationError("camera_selection_required", "No matching camera, or multiple cameras present. Set TELESCO_PI_CAMERA_ID explicitly.")
            self._handle = sdk.Nncam.Open(selected.id)
            if self._handle is None:
                raise DeviceOperationError("camera_open_failed", "Nncam could not open the selected camera.")
            self._name = selected.displayname
            self._width, self._height = self._handle.get_Size()
            if not (0 < self._width <= 16384 and 0 < self._height <= 16384):
                raise DeviceOperationError("camera_dimensions", "Nncam returned invalid frame dimensions.")
            self._handle.put_Option(sdk.NNCAM_OPTION_RAW, 1)
            self._handle.put_Option(sdk.NNCAM_OPTION_BITDEPTH, 0)
            self._apply_configuration(self._configuration)
            self._handle.StartPullModeWithCallback(self._callback, self)
        except self._sdk_errors as exc:
            raise DeviceOperationError("camera_sdk_error", f"Nncam initialization failed: {exc}") from exc

    async def connect(self) -> DeviceCommandResult:
        async with self._lock:
            if self._handle is not None:
                self._connected()
                return DeviceCommandResult(accepted=True, message="Camera already connected.")
            self._error = None
            try:
                await asyncio.to_thread(self._open)
            except DeviceOperationError as exc:
                self._error = DeviceErrorInfo(code=exc.code, message=exc.message)
                if self._handle is not None:
                    try:
                        await asyncio.to_thread(self._close)
                    except self._sdk_errors as cleanup_error:
                        self._error = DeviceErrorInfo(
                            code="camera_cleanup_failed",
                            message=f"{exc.message} Camera cleanup also failed: {cleanup_error}",
                        )
                        raise DeviceOperationError(self._error.code, self._error.message) from cleanup_error
                raise
        return DeviceCommandResult(accepted=True, message="Nncam camera connected (8-bit raw full-frame).")

    def _close(self) -> None:
        handle = self._handle
        try:
            if handle is not None:
                try:
                    handle.Stop()
                finally:
                    handle.Close()
        finally:
            self._handle = None
            with self._condition:
                self._frame = None
                self._preview_active = False
                self._condition.notify_all()

    async def disconnect(self) -> DeviceCommandResult:
        async with self._lock:
            try:
                await asyncio.to_thread(self._close)
            except self._sdk_errors as exc:
                self._error = DeviceErrorInfo(code="camera_sdk_error", message=f"Nncam close failed: {exc}")
                raise DeviceOperationError(self._error.code, self._error.message) from exc
            self._error = None
        return DeviceCommandResult(accepted=True, message="Nncam camera disconnected.")

    async def get_status(self) -> DeviceStatus:
        return DeviceStatus(
            device_id=self.device_id, kind=DeviceKind.CAMERA, name=self._name,
            implementation=DeviceImplementation.REAL,
            connection_state=DeviceConnectionState.ERROR if self._error else (
                DeviceConnectionState.CONNECTED if self._handle else DeviceConnectionState.DISCONNECTED
            ),
            health=DeviceHealth.ERROR if self._error else DeviceHealth.WARNING,
            message=self._error.message if self._error else "External Nncam SDK; physical validation pending. Not a Player One driver.",
            capabilities=DeviceCapabilities(
                supports_preview=True, supports_still_capture=True,
                notes=["8-bit raw monochrome PNG. Full-frame, binning 1. No scientific 16-bit or sequence capture yet."],
            ),
            metadata={"configuration": self._configuration.model_dump(), "preview_active": self._preview_active,
                      "hardware_validation": "pending", "source": "Camera_Control_Photsat", "width": self._width, "height": self._height},
            error=self._error,
        )

    async def configure(self, configuration: CameraConfiguration) -> DeviceCommandResult:
        async with self._lock:
            try:
                await asyncio.to_thread(self._apply_configuration, configuration)
            except self._sdk_errors as exc:
                self._error = DeviceErrorInfo(code="camera_sdk_error", message=f"Nncam configuration failed; reconnect before retrying: {exc}")
                raise DeviceOperationError(self._error.code, self._error.message) from exc
        return DeviceCommandResult(accepted=True, message="Camera exposure and gain configured.")

    def _capture(self) -> CapturedFrame:
        self._connected()
        with self._condition:
            generation = self._generation
            ready = self._condition.wait_for(
                lambda: self._generation > generation or self._error is not None,
                timeout=self._configuration.exposure_ms / 1000 + self.settings.device_timeout_seconds,
            )
            self._connected()
            if not ready or self._frame is None:
                raise DeviceOperationError("camera_frame_timeout", "No new camera frame arrived before the deadline.")
            raw = self._frame
        stride = ((self._width + 3) // 4) * 4
        image = np.frombuffer(raw, dtype=np.uint8).reshape(self._height, stride)[:, :self._width]
        ok, encoded = cv2.imencode(".png", image)
        if not ok:
            raise DeviceOperationError("camera_encode_failed", "Could not encode camera frame.")
        return CapturedFrame(
            format="png", bytes_payload=encoded.tobytes(), width=self._width, height=self._height,
            metadata={"exposure_ms": self._configuration.exposure_ms, "gain": self._configuration.gain,
                      "generated_by": "nncam", "bit_depth": 8, "raw": True},
        )

    async def capture_still(self) -> CapturedFrame:
        async with self._lock:
            return await asyncio.to_thread(self._capture)

    async def start_preview(self) -> DeviceCommandResult:
        self._connected()
        self._preview_active = True
        return DeviceCommandResult(accepted=True, message="Camera preview enabled.")

    async def stop_preview(self) -> DeviceCommandResult:
        self._preview_active = False
        return DeviceCommandResult(accepted=True, message="Camera preview disabled.")
