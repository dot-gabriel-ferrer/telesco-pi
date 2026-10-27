"""Minimal Linux ctypes binding to the external Player One Camera SDK 3.x ABI."""

from __future__ import annotations

import argparse
import ctypes as ct
import json
from pathlib import Path
import platform

from libs.devices.interfaces import DeviceOperationError


class CameraProperties(ct.Structure):
    _fields_ = [
        ("cameraModelName", ct.c_char * 256), ("userCustomID", ct.c_char * 16),
        ("cameraID", ct.c_int), ("maxWidth", ct.c_int), ("maxHeight", ct.c_int),
        ("bitDepth", ct.c_int), ("isColorCamera", ct.c_int), ("isHasST4Port", ct.c_int),
        ("isHasCooler", ct.c_int), ("isUSB3Speed", ct.c_int), ("bayerPattern", ct.c_int),
        ("pixelSize", ct.c_double), ("SN", ct.c_char * 64),
        ("sensorModelName", ct.c_char * 32), ("localPath", ct.c_char * 256),
        ("bins", ct.c_int * 8), ("imgFormats", ct.c_int * 8),
        ("isSupportHardBin", ct.c_int), ("pID", ct.c_int), ("reserved", ct.c_char * 248),
    ]


class ConfigValue(ct.Union):
    _fields_ = [("intValue", ct.c_long), ("floatValue", ct.c_double), ("boolValue", ct.c_int)]


class ConfigAttributes(ct.Structure):
    _fields_ = [
        ("isSupportAuto", ct.c_int), ("isWritable", ct.c_int), ("isReadable", ct.c_int),
        ("configID", ct.c_int), ("valueType", ct.c_int),
        ("maxValue", ConfigValue), ("minValue", ConfigValue), ("defaultValue", ConfigValue),
        ("szConfName", ct.c_char * 64), ("szDescription", ct.c_char * 128),
        ("reserved", ct.c_char * 64),
    ]


def library_path(root: Path) -> Path:
    architecture = platform.machine().lower()
    directory = {"aarch64": "arm64", "arm64": "arm64", "x86_64": "x64", "amd64": "x64"}.get(architecture)
    if platform.system() != "Linux" or directory is None or ct.sizeof(ct.c_void_p) != 8:
        raise DeviceOperationError("player_one_platform", "This adapter requires 64-bit Linux (aarch64 or x86_64).")
    return root / "lib" / directory / "libPlayerOneCamera.so.3.10.1"


def text(value: bytes) -> str:
    return value.decode("utf-8", errors="replace")


class PlayerOneSdk:
    def __init__(self, root: Path) -> None:
        path = library_path(root).resolve()
        try:
            self.library = ct.CDLL(str(path))
            signatures = {
                "POAGetCameraCount": (ct.c_int, []),
                "POAGetCameraProperties": (ct.c_int, [ct.c_int, ct.POINTER(CameraProperties)]),
                "POAGetSDKVersion": (ct.c_char_p, []),
                "POAGetAPIVersion": (ct.c_int, []),
                "POAGetErrorString": (ct.c_char_p, [ct.c_int]),
                "POAOpenCamera": (ct.c_int, [ct.c_int]),
                "POAInitCamera": (ct.c_int, [ct.c_int]),
                "POACloseCamera": (ct.c_int, [ct.c_int]),
                "POAStopExposure": (ct.c_int, [ct.c_int]),
                "POAStartExposure": (ct.c_int, [ct.c_int, ct.c_int]),
                "POAGetImageData": (ct.c_int, [ct.c_int, ct.c_void_p, ct.c_long, ct.c_int]),
                "POAGetConfigAttributesByConfigID": (ct.c_int, [ct.c_int, ct.c_int, ct.POINTER(ConfigAttributes)]),
                "POASetConfig": (ct.c_int, [ct.c_int, ct.c_int, ConfigValue, ct.c_int]),
                "POAGetConfig": (ct.c_int, [ct.c_int, ct.c_int, ct.POINTER(ConfigValue), ct.POINTER(ct.c_int)]),
                "POASetImageBin": (ct.c_int, [ct.c_int, ct.c_int]),
                "POASetImageSize": (ct.c_int, [ct.c_int, ct.c_int, ct.c_int]),
                "POASetImageStartPos": (ct.c_int, [ct.c_int, ct.c_int, ct.c_int]),
                "POASetImageFormat": (ct.c_int, [ct.c_int, ct.c_int]),
                "POAGetImageFormat": (ct.c_int, [ct.c_int, ct.POINTER(ct.c_int)]),
                "POAGetImageSize": (ct.c_int, [ct.c_int, ct.POINTER(ct.c_int), ct.POINTER(ct.c_int)]),
            }
            for name, (result, arguments) in signatures.items():
                function = getattr(self.library, name)
                function.restype = result
                function.argtypes = arguments
        except (OSError, AttributeError) as exc:
            raise DeviceOperationError(
                "player_one_sdk_unavailable",
                f"Cannot load Player One SDK at {path}. Check architecture, version and libusb-1.0.so.0: {exc}",
            ) from exc
        self.version = text(self.library.POAGetSDKVersion() or b"")
        if self.version != "3.10.1":
            raise DeviceOperationError("player_one_sdk_version", f"Expected SDK 3.10.1, got {self.version!r}.")

    def call(self, name: str, *arguments: object) -> None:
        code = getattr(self.library, name)(*arguments)
        if code != 0:
            description = text(self.library.POAGetErrorString(code) or b"Unknown error")
            raise DeviceOperationError(
                "player_one_timeout" if code == 9 else "player_one_sdk_error",
                f"{name} failed ({code}): {description}",
            )

    def enumerate(self) -> list[CameraProperties]:
        count = self.library.POAGetCameraCount()
        if not 0 <= count <= 256:
            raise DeviceOperationError("player_one_enumeration", f"Invalid camera count: {count}")
        cameras = []
        for index in range(count):
            properties = CameraProperties()
            try:
                self.call("POAGetCameraProperties", index, ct.byref(properties))
            except DeviceOperationError as exc:
                raise DeviceOperationError(
                    exc.code, f"{exc.message} Check USB read/write permissions for the current user; enumeration can count inaccessible devices. Do not run the backend as root.",
                ) from exc
            cameras.append(properties)
        return cameras

    def attributes(self, camera_id: int, config_id: int) -> ConfigAttributes:
        attributes = ConfigAttributes()
        self.call("POAGetConfigAttributesByConfigID", camera_id, config_id, ct.byref(attributes))
        if attributes.valueType != 0 or not attributes.isWritable or not attributes.isReadable:
            raise DeviceOperationError("player_one_config_type", "Exposure/gain must be readable and writable integer controls.")
        return attributes

    def set_integer(self, camera_id: int, config_id: int, value: int) -> None:
        setting = ConfigValue()
        setting.intValue = value
        self.call("POASetConfig", camera_id, config_id, setting, 0)

    def get_integer(self, camera_id: int, config_id: int) -> tuple[int, bool]:
        value, automatic = ConfigValue(), ct.c_int()
        self.call("POAGetConfig", camera_id, config_id, ct.byref(value), ct.byref(automatic))
        return value.intValue, bool(automatic.value)

    def size(self, camera_id: int) -> tuple[int, int]:
        width, height = ct.c_int(), ct.c_int()
        self.call("POAGetImageSize", camera_id, ct.byref(width), ct.byref(height))
        return width.value, height.value


def probe(root: Path) -> dict:
    sdk = PlayerOneSdk(root)
    cameras = sdk.enumerate()
    return {
        "sdk_version": sdk.version, "api_version": sdk.library.POAGetAPIVersion(),
        "architecture": platform.machine(), "library": str(library_path(root).resolve()),
        "operation": "enumeration_only_no_open_no_exposure",
        "camera_count": len(cameras),
        "cameras": [
            {"camera_id": camera.cameraID, "model": text(camera.cameraModelName),
             "serial": text(camera.SN), "width": camera.maxWidth, "height": camera.maxHeight,
             "adc_bit_depth": camera.bitDepth, "usb3": bool(camera.isUSB3Speed),
             "monochrome": not bool(camera.isColorCamera)}
            for camera in cameras
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read-only Player One SDK probe; never opens or exposes cameras.")
    parser.add_argument("--sdk-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(probe(args.sdk_root), indent=2))
    except DeviceOperationError as exc:
        parser.exit(1, f"{exc.code}: {exc.message}\n")
