import asyncio
import ctypes as ct
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import threading
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from libs.config.settings import Settings
from libs.devices.imaging import preview_png
from libs.devices.interfaces import DeviceOperationError
from libs.devices.models import CameraConfiguration
from libs.devices.player_one import PlayerOneCameraDriver
from libs.devices.player_one_sdk import CameraProperties, ConfigAttributes, ConfigValue, PlayerOneSdk, library_path


class FakeSdk:
    version = "3.10.1"

    def __init__(self):
        self.camera = CameraProperties()
        self.camera.cameraID = 7
        self.camera.cameraModelName = b"Player One Mars-M"
        self.camera.SN = b"MARS-TEST"
        self.camera.maxWidth, self.camera.maxHeight = 8, 4
        self.camera.bitDepth = 12
        self.camera.bins[0] = 1
        self.camera.imgFormats[:] = [0, 1, -1, -1, -1, -1, -1, -1]
        self.calls = []
        self.values = {0: 50000, 1: 100}
        self.fail = None
        self.block = None
        self.format = 1
        self.readback_mismatch = False
        self.multiple = False

    def enumerate(self):
        return [self.camera] * (2 if self.multiple else 1)

    def attributes(self, camera_id, config_id):
        attributes = ConfigAttributes()
        attributes.minValue.intValue = 1000 if config_id == 0 else 0
        attributes.maxValue.intValue = 60000000 if config_id == 0 else 500
        return attributes

    def set_integer(self, camera_id, config_id, value):
        self.values[config_id] = value

    def get_integer(self, camera_id, config_id):
        return self.values[config_id] + int(self.readback_mismatch), False

    def size(self, camera_id):
        return 8, 4

    def call(self, name, *arguments):
        self.calls.append((name, arguments))
        if self.fail == name:
            raise DeviceOperationError("player_one_timeout", "Injected SDK failure")
        if name == "POASetImageFormat":
            self.format = arguments[1]
        if name == "POAGetImageFormat":
            ct.cast(arguments[1], ct.POINTER(ct.c_int))[0] = self.format
        if name == "POAGetImageData":
            if self.block is not None:
                self.block.wait(timeout=2)
            dtype = np.dtype("<u2") if self.format == 1 else np.uint8
            image = np.arange(32, dtype=dtype).reshape(4, 8)
            if self.format == 1:
                image *= 2048
            assert image.nbytes == arguments[2]
            assert arguments[3] == self.values[0] // 1000 + 2000
            ct.memmove(arguments[1], image.ctypes.data, image.nbytes)


@pytest.fixture
def player(monkeypatch, tmp_path):
    sdk = FakeSdk()
    monkeypatch.setattr("libs.devices.player_one.PlayerOneSdk", lambda root: sdk)
    driver = PlayerOneCameraDriver(Settings(
        player_one_sdk_root=tmp_path, camera_id="MARS-TEST",
    ))
    return driver, sdk


async def test_raw16_capture_readback_and_preview(player):
    driver, sdk = player
    try:
        await driver.connect()
        await driver.configure(CameraConfiguration(exposure_ms=20, gain=150))
        assert sdk.values == {0: 20000, 1: 150}
        await driver.start_preview()
        frame = await driver.capture_still()
        raw = cv2.imdecode(np.frombuffer(frame.bytes_payload, np.uint8), cv2.IMREAD_UNCHANGED)
        assert raw.dtype == np.uint16 and raw.shape == (4, 8)
        assert raw[3, 7] == 31 * 2048
        assert frame.metadata["bit_depth"] == 16
        preview = cv2.imdecode(np.frombuffer(preview_png(frame), np.uint8), cv2.IMREAD_UNCHANGED)
        assert preview.dtype == np.uint8 and preview[3, 7] == 248
        assert (await driver.get_status()).metadata["preview_active"]
        await driver.stop_preview()
        assert not (await driver.get_status()).metadata["preview_active"]
    finally:
        await driver.disconnect()
    assert [name for name, _ in sdk.calls][-2:] == ["POAStopExposure", "POACloseCamera"]


async def test_raw8_capture(player):
    driver, _ = player
    driver.settings.player_one_bit_depth = 8
    try:
        await driver.connect()
        frame = await driver.capture_still()
        image = cv2.imdecode(np.frombuffer(frame.bytes_payload, np.uint8), cv2.IMREAD_UNCHANGED)
        assert image.dtype == np.uint8 and image[3, 7] == 31
    finally:
        await driver.disconnect()


async def test_invalid_config_does_not_mutate_camera(player):
    driver, sdk = player
    try:
        await driver.connect()
        for configuration in (CameraConfiguration(gain=501), CameraConfiguration(binning=2), CameraConfiguration(roi={"width": 8})):
            with pytest.raises(DeviceOperationError):
                await driver.configure(configuration)
        assert sdk.values == {0: 50000, 1: 100}
        assert (await driver.get_status()).connection_state.value == "connected"
        sdk.readback_mismatch = True
        with pytest.raises(DeviceOperationError, match="retain"):
            await driver.configure(CameraConfiguration(exposure_ms=10))
        assert (await driver.get_status()).connection_state.value == "error"
    finally:
        await driver.disconnect()


@pytest.mark.parametrize("change", ["model", "generation", "multiple", "serial"])
async def test_selects_only_expected_mars_m(player, change):
    driver, sdk = player
    if change == "model":
        sdk.camera.cameraModelName = b"Neptune-M"
    elif change == "generation":
        sdk.camera.cameraModelName = b"Player One Mars-M II"
    elif change == "multiple":
        sdk.multiple = True
    else:
        driver.settings.camera_id = "wrong-camera"
    with pytest.raises(DeviceOperationError, match="Exactly one"):
        await driver.connect()
    assert not any(name == "POAOpenCamera" for name, _ in sdk.calls)


@pytest.mark.parametrize("pattern", range(4))
async def test_mars_c_preserves_raw_and_demosaics_preview(player, pattern):
    driver, sdk = player
    sdk.camera.cameraModelName = b"Player One Mars-C"
    sdk.camera.isColorCamera = 1
    sdk.camera.bayerPattern = pattern
    try:
        await driver.connect()
        frame = await driver.capture_still()
        image = cv2.imdecode(np.frombuffer(frame.bytes_payload, np.uint8), cv2.IMREAD_UNCHANGED)
        assert image.dtype == np.uint16 and image.ndim == 2
        preview = cv2.imdecode(np.frombuffer(preview_png(frame), np.uint8), cv2.IMREAD_UNCHANGED)
        assert preview.dtype == np.uint8 and preview.shape == (4, 8, 3)
        assert frame.metadata["bayer_pattern"] == ("RGGB", "BGGR", "GRBG", "GBRG")[pattern]
    finally:
        await driver.disconnect()


async def test_failed_init_closes_and_missing_root_errors(player):
    driver, sdk = player
    sdk.fail = "POAInitCamera"
    with pytest.raises(DeviceOperationError):
        await driver.connect()
    assert [name for name, _ in sdk.calls][-2:] == ["POAStopExposure", "POACloseCamera"]
    driver.settings.player_one_sdk_root = None
    with pytest.raises(DeviceOperationError, match="SDK_ROOT"):
        await driver.connect()


async def test_timeout_requires_reconnection_and_stops_exposure(player):
    driver, sdk = player
    try:
        await driver.connect()
        await driver.start_preview()
        sdk.fail = "POAGetImageData"
        with pytest.raises(DeviceOperationError):
            await driver.capture_still()
        assert sdk.calls[-1][0] == "POAStopExposure"
        assert (await driver.get_status()).connection_state.value == "error"
        assert not (await driver.get_status()).metadata["preview_active"]
        with pytest.raises(DeviceOperationError):
            await driver.capture_still()
    finally:
        await driver.disconnect()


async def test_failed_close_retains_handle_for_explicit_cleanup(player):
    driver, sdk = player
    await driver.connect()
    sdk.fail = "POACloseCamera"
    with pytest.raises(DeviceOperationError):
        await driver.disconnect()
    assert driver._camera is not None
    assert (await driver.get_status()).connection_state.value == "error"
    with pytest.raises(DeviceOperationError):
        await driver.connect()
    sdk.fail = None
    await driver.disconnect()
    assert driver._camera is None


async def test_cancellation_does_not_close_camera_during_native_read(player):
    driver, sdk = player
    await driver.connect()
    sdk.block = threading.Event()
    capture = asyncio.create_task(driver.capture_still())
    try:
        for _ in range(100):
            if sdk.calls[-1][0] == "POAGetImageData":
                break
            await asyncio.sleep(.005)
        assert sdk.calls[-1][0] == "POAGetImageData"
        capture.cancel()
        close = asyncio.create_task(driver.disconnect())
        await asyncio.sleep(.02)
        assert not close.done()
        capture.cancel()
        await asyncio.sleep(.02)
        assert not close.done()
        sdk.block.set()
        with pytest.raises(asyncio.CancelledError):
            await capture
        await close
    finally:
        sdk.block.set()
        await driver.disconnect()


async def test_cancelled_connection_closes_camera(player, monkeypatch):
    driver, sdk = player
    entered, release = threading.Event(), threading.Event()
    original_call = sdk.call
    def blocking_call(name, *args):
        if name == "POAInitCamera":
            entered.set()
            release.wait(timeout=2)
        original_call(name, *args)
    monkeypatch.setattr(sdk, "call", blocking_call)
    connecting = asyncio.create_task(driver.connect())
    for _ in range(100):
        if entered.is_set():
            break
        await asyncio.sleep(.005)
    assert entered.is_set()
    connecting.cancel()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await connecting
    assert sdk.calls[-1][0] == "POACloseCamera"
    assert driver._camera is None


def test_binding_signatures_and_sdk_errors(monkeypatch, tmp_path):
    class Function:
        def __init__(self, value):
            self.value = value
        def __call__(self, *args):
            return self.value
    library = SimpleNamespace()
    def get_function(name):
        if name not in library.__dict__:
            value = b"3.10.1" if name == "POAGetSDKVersion" else b"timeout" if name == "POAGetErrorString" else 0
            setattr(library, name, Function(value))
        return library.__dict__[name]
    class DynamicLibrary:
        def __getattr__(self, name):
            return get_function(name)
    monkeypatch.setattr(ct, "CDLL", lambda path: DynamicLibrary())
    sdk = PlayerOneSdk(tmp_path)
    assert sdk.enumerate() == []
    assert get_function("POAGetImageData").argtypes == [ct.c_int, ct.c_void_p, ct.c_long, ct.c_int]
    assert get_function("POASetConfig").argtypes[2] is ConfigValue
    get_function("POAStopExposure").value = 9
    with pytest.raises(DeviceOperationError, match="timeout"):
        sdk.call("POAStopExposure", 7)
    get_function("POAGetSDKVersion").value = b"0.0.0"
    with pytest.raises(DeviceOperationError, match="Expected SDK"):
        PlayerOneSdk(tmp_path)


def test_architecture_selection(monkeypatch, tmp_path):
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setattr("platform.machine", lambda: "aarch64")
    assert library_path(tmp_path) == tmp_path / "lib/arm64/libPlayerOneCamera.so.3.10.1"
    monkeypatch.setattr("platform.machine", lambda: "armv7l")
    with pytest.raises(DeviceOperationError, match="64-bit"):
        library_path(tmp_path)


def test_abi_against_official_header_when_available(tmp_path):
    root = Path(__file__).resolve().parents[2]
    include = root / ".local-sdk/player-one/PlayerOne_Camera_SDK_Linux_V3.10.1/include"
    compiler = shutil.which("cc")
    if compiler is None or not (include / "PlayerOneCamera.h").is_file():
        pytest.skip("Optional ABI verification requires downloaded official SDK and C compiler.")
    source = tmp_path / "abi.c"
    source.write_text(
        '#include <stddef.h>\n#include <stdio.h>\n#include "PlayerOneCamera.h"\n'
        'int main(void) { printf("%zu %zu %zu %zu %zu %zu\\n", '
        'sizeof(POACameraProperties), sizeof(POAConfigValue), sizeof(POAConfigAttributes), '
        'offsetof(POACameraProperties, pixelSize), offsetof(POACameraProperties, reserved), '
        'offsetof(POAConfigAttributes, maxValue)); return 0; }\n'
    )
    executable = tmp_path / "abi"
    subprocess.run([compiler, str(source), "-I", str(include), "-o", str(executable)], check=True, capture_output=True)
    actual = subprocess.run([str(executable)], check=True, capture_output=True, text=True).stdout.split()
    expected = [
        ct.sizeof(CameraProperties), ct.sizeof(ConfigValue), ct.sizeof(ConfigAttributes),
        CameraProperties.pixelSize.offset, CameraProperties.reserved.offset,
        ConfigAttributes.maxValue.offset,
    ]
    assert list(map(int, actual)) == expected


@pytest.mark.parametrize("fail", [False, True])
async def test_opt_in_camera_bench_with_fake_sdk(player, monkeypatch, tmp_path, fail):
    driver, sdk = player
    driver.settings.device_mode = "configured"
    driver.settings.camera_driver = "player_one"
    path = Path(__file__).resolve().parents[1] / "hardware/test_player_one_camera.py"
    function = runpy.run_path(str(path))["test_player_one_raw16_bench"]
    monkeypatch.setitem(function.__globals__, "Settings", lambda: driver.settings)
    monkeypatch.setitem(function.__globals__, "PlayerOneCameraDriver", lambda settings: driver)
    monkeypatch.setattr("platform.machine", lambda: "aarch64")
    monkeypatch.setattr("shutil.disk_usage", lambda path: SimpleNamespace(free=100 * 1024**3))
    evidence = tmp_path / "camera-evidence"
    monkeypatch.setenv("TELESCO_PI_HARDWARE_EVIDENCE_DIR", str(evidence))
    monkeypatch.setenv("TELESCO_PI_HARDWARE_FRAMES", "2")
    if fail:
        sdk.fail = "POAGetImageData"
        with pytest.raises(DeviceOperationError):
            await function()
    else:
        await function()
    report = json.loads((evidence / "camera-bench.json").read_text())
    assert report["status"] == ("FAIL" if fail else "PASS")
    assert len(report["samples"]) == (0 if fail else 2)
    assert sdk.calls[-1][0] == "POACloseCamera"
