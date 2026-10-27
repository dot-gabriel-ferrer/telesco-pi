import asyncio
import ctypes
import sys
import threading
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from pydantic import ValidationError

from libs.config.settings import Settings
from libs.devices.interfaces import DeviceOperationError
from libs.devices.models import CameraConfiguration, DeviceConnectionState, MountCoordinates, TrackingMode
from libs.devices.nncam import NncamCameraDriver
from libs.devices.skywatcher import SkyWatcherUdpMountDriver, decode_u24, encode_u24


class MotorController(asyncio.DatagramProtocol):
    def __init__(self):
        self.commands = []
        self.drop = False
        self.reject = None
        self.busy = False

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, address):
        text = data.decode("ascii")
        self.commands.append(text)
        if self.drop:
            return
        command = text[1]
        if command == self.reject:
            reply = "!2\r"
        elif command == "a":
            reply = f"={encode_u24(360000)}\r"
        elif command == "b":
            reply = f"={encode_u24(100000)}\r"
        elif command == "e":
            reply = "=010203\r"
        elif command == "f":
            reply = "=000100\r" if self.busy else "=000000\r"
        else:
            reply = "=\r"
        self.transport.sendto(reply.encode("ascii"), address)


@pytest.fixture
async def mount():
    loop = asyncio.get_running_loop()
    transport, controller = await loop.create_datagram_endpoint(MotorController, local_addr=("127.0.0.1", 0))
    driver = SkyWatcherUdpMountDriver(Settings(
        mount_host="127.0.0.1", mount_port=transport.get_extra_info("sockname")[1],
        device_timeout_seconds=0.05,
        mount_motion_enabled=True,
    ))
    yield driver, controller
    await driver.disconnect()
    transport.close()


def test_protocol_and_input_limits():
    assert encode_u24(0x123456) == "563412"
    assert decode_u24("563412") == 0x123456
    for invalid in ("GG0011", "", "01", "00 01 "):
        with pytest.raises(DeviceOperationError):
            decode_u24(invalid)
    with pytest.raises(DeviceOperationError):
        encode_u24(0x1000000)
    for data in ({"gain": -1}, {"exposure_ms": 0}, {"roi": {"width": 0}}):
        with pytest.raises(ValidationError):
            CameraConfiguration(**data)
    with pytest.raises(ValidationError):
        MountCoordinates(azimuth_deg=float("nan"), altitude_deg=20)


async def test_mount_relative_motion_stop_and_unsupported(mount):
    driver, controller = mount
    await driver.connect()
    assert (await driver.get_status()).connection_state == DeviceConnectionState.CONNECTED
    result = await driver.manual_slew(1, -0.5)
    assert result.accepted and result.status == "pending"
    assert ":G120\r" in controller.commands
    assert ":G221\r" in controller.commands
    assert f":H1{encode_u24(1000)}\r" in controller.commands
    assert f":H2{encode_u24(500)}\r" in controller.commands
    assert f":I1{encode_u24(400)}\r" in controller.commands
    await driver.stop()
    assert controller.commands[-2:] == [":K1\r", ":K2\r"]
    for mode in (TrackingMode.SIDEREAL, TrackingMode.SOLAR, TrackingMode.LUNAR):
        with pytest.raises(DeviceOperationError, match="calibrated"):
            await driver.set_tracking_mode(mode)
    with pytest.raises(DeviceOperationError):
        await driver.goto(MountCoordinates(azimuth_deg=10, altitude_deg=20))
    with pytest.raises(DeviceOperationError):
        await driver.manual_slew(2, 0)


async def test_mount_busy_rejection_and_timeout(mount):
    driver, controller = mount
    await driver.connect()
    controller.busy = True
    with pytest.raises(DeviceOperationError, match="moving"):
        await driver.manual_slew(1, 0)
    assert not any(command.startswith(":J") for command in controller.commands)
    controller.busy = False
    controller.reject = "J"
    with pytest.raises(DeviceOperationError, match="rejected"):
        await driver.manual_slew(1, 0)
    assert controller.commands[-2:] == [":K1\r", ":K2\r"]
    controller.drop = True
    with pytest.raises(DeviceOperationError, match="unknown"):
        await driver.stop()
    assert (await driver.get_status()).connection_state == DeviceConnectionState.ERROR
    with pytest.raises(DeviceOperationError):
        await driver.stop()


async def test_physical_motion_is_disabled_by_default(mount):
    driver, controller = mount
    assert Settings().mount_motion_enabled is False
    driver.settings.mount_motion_enabled = False
    await driver.connect()
    count = len(controller.commands)
    with pytest.raises(DeviceOperationError, match="disabled"):
        await driver.manual_slew(.1, 0)
    assert len(controller.commands) == count
    assert not (await driver.get_status()).capabilities.supports_manual_slew
    await driver.stop()
    assert controller.commands[-2:] == [":K1\r", ":K2\r"]


class FakeNncamHandle:
    def __init__(self):
        self.closed = False
        self.stopped = threading.Event()
        self.thread = None
        self.exposure = None
        self.gain = None

    def get_Size(self):
        return 5, 4

    def get_ExpTimeRange(self):
        return 1000, 1000000, 50000

    def get_ExpoAGainRange(self):
        return 100, 500, 100

    def put_AutoExpoEnable(self, value):
        assert value == 0

    def put_ExpoTime(self, value):
        self.exposure = value

    def put_ExpoAGain(self, value):
        self.gain = value

    def put_Option(self, option, value):
        pass

    def StartPullModeWithCallback(self, callback, context):
        self.callback = callback
        def emit():
            while not self.stopped.wait(0.01):
                callback(4, context)
        self.thread = threading.Thread(target=emit)
        self.thread.start()

    def PullImageV4(self, buffer, still, bits, pitch, info):
        assert bits == 8 and pitch == 8
        ctypes.memmove(buffer, bytes([42] * 5 + [0] * 3) * 4, 32)

    def Stop(self):
        self.stopped.set()
        if self.thread:
            self.thread.join(timeout=1)

    def Close(self):
        self.Stop()
        self.closed = True


@pytest.fixture
def nncam(monkeypatch):
    handle = FakeNncamHandle()
    devices = [SimpleNamespace(id="cam-1", displayname="Test EHD")]
    sdk = SimpleNamespace(
        Nncam=SimpleNamespace(EnumV2=lambda: devices, Open=lambda camera_id: handle),
        HRESULTException=RuntimeError,
        NNCAM_OPTION_RAW=1, NNCAM_OPTION_BITDEPTH=2,
        NNCAM_EVENT_IMAGE=4, NNCAM_EVENT_ERROR=5, NNCAM_EVENT_DISCONNECTED=6,
    )
    monkeypatch.setitem(sys.modules, "fake_nncam", sdk)
    return NncamCameraDriver(Settings(camera_sdk_module="fake_nncam", device_timeout_seconds=0.05)), handle, sdk, devices


async def test_nncam_configuration_capture_and_disconnect(nncam):
    driver, handle, _, _ = nncam
    try:
        await driver.connect()
        await driver.configure(CameraConfiguration(exposure_ms=10, gain=200))
        assert handle.exposure == 10000 and handle.gain == 200
        frame = await driver.capture_still()
        image = cv2.imdecode(np.frombuffer(frame.bytes_payload, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        assert image.shape == (4, 5)
        assert np.all(image == 42)
        await driver.start_preview()
        assert (await driver.get_status()).metadata["preview_active"]
        for config in (CameraConfiguration(gain=99), CameraConfiguration(binning=2)):
            with pytest.raises(DeviceOperationError):
                await driver.configure(config)
        handle.callback(6, driver)
        with pytest.raises(DeviceOperationError):
            await driver.capture_still()
    finally:
        await driver.disconnect()
    assert handle.closed


async def test_nncam_missing_sdk_and_ambiguous_selection(nncam):
    driver = NncamCameraDriver(Settings(camera_sdk_module="nonexistent_telesco_sdk"))
    with pytest.raises(DeviceOperationError, match="authorized"):
        await driver.connect()
    driver, handle, sdk, devices = nncam
    devices.append(SimpleNamespace(id="cam-2", displayname="Other EHD"))
    with pytest.raises(DeviceOperationError, match="multiple"):
        await driver.connect()
    assert not handle.closed


async def test_nncam_frame_timeout(nncam):
    driver, handle, _, _ = nncam
    try:
        await driver.connect()
        handle.Stop()
        with pytest.raises(DeviceOperationError, match="deadline"):
            await driver.capture_still()
    finally:
        await driver.disconnect()


async def test_nncam_failed_initialization_closes_device(nncam, monkeypatch):
    driver, handle, _, _ = nncam
    def fail_start(*args):
        raise RuntimeError("Stream unavailable")
    monkeypatch.setattr(handle, "StartPullModeWithCallback", fail_start)
    with pytest.raises(DeviceOperationError, match="initialization failed"):
        await driver.connect()
    assert handle.closed
    assert (await driver.get_status()).connection_state == DeviceConnectionState.ERROR
    await driver.disconnect()
