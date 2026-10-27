"""Explicit opt-in camera bench; never instantiates or controls a mount."""

import asyncio
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import time
from datetime import datetime, timezone

import cv2
import numpy as np
import pytest

from libs.config.settings import Settings
from libs.devices.imaging import preview_png
from libs.devices.models import CameraConfiguration
from libs.devices.player_one import PlayerOneCameraDriver

pytestmark = pytest.mark.skipif(
    os.environ.get("TELESCO_PI_RUN_HARDWARE_CAMERA") != "1",
    reason="Physical camera bench requires current operator approval and explicit opt-in.",
)


async def test_player_one_raw16_bench():
    assert platform.machine().lower() in ("aarch64", "arm64", "x86_64", "amd64"), "This bench requires 64-bit Linux."
    settings = Settings()
    assert settings.device_mode == "configured" and settings.camera_driver == "player_one"
    assert not settings.mount_motion_enabled, "Run camera-only checks with physical motion disabled."
    assert settings.player_one_bit_depth == 16
    assert settings.camera_id and "REPLACE" not in settings.camera_id, "An explicit verified serial is required."
    directory = Path(os.environ["TELESCO_PI_HARDWARE_EVIDENCE_DIR"])
    assert directory.is_absolute(), "Evidence directory must be absolute and new."
    frames = int(os.environ.get("TELESCO_PI_HARDWARE_FRAMES", "100"))
    interval = float(os.environ.get("TELESCO_PI_HARDWARE_INTERVAL_SECONDS", "0"))
    assert 1 <= frames <= 1000 and 0 <= interval <= 10
    directory.mkdir(parents=True, exist_ok=False)
    report = {
        "started_at": datetime.now(timezone.utc).isoformat(), "status": "FAIL",
        "serial": settings.camera_id, "sdk_version": "3.10.1", "architecture": platform.machine(),
        "configuration": {"exposure_ms": 50, "gain": 100, "bit_depth": 16},
        "requested_frames": frames, "interval_seconds": interval, "samples": [],
    }
    driver = PlayerOneCameraDriver(settings)
    started = time.monotonic()
    try:
        try:
            await driver.connect()
            await driver.configure(CameraConfiguration(exposure_ms=50, gain=100))
            status = await driver.get_status()
            assert status.metadata["camera_serial"] == settings.camera_id, "Use the verified serial, not the transient SDK ID."
            report["device"] = status.model_dump(mode="json")
            required = int(status.metadata["width"] * status.metadata["height"] * 2 * frames * 1.1) + 2 * 1024**3
            assert shutil.disk_usage(directory).free >= required, f"Need {required} free bytes including 2 GiB reserve."
            await driver.start_preview()
            for index in range(frames):
                start_frame = time.monotonic()
                frame = await driver.capture_still()
                elapsed = time.monotonic() - start_frame
                image = cv2.imdecode(np.frombuffer(frame.bytes_payload, np.uint8), cv2.IMREAD_UNCHANGED)
                assert image is not None and image.dtype == np.uint16
                assert image.shape == (frame.height, frame.width)
                minimum, maximum = int(image.min()), int(image.max())
                assert minimum != maximum, "Constant frame: inspect camera/lens/cap with the operator."
                name = f"frame-{index:04d}.png"
                (directory / name).write_bytes(frame.bytes_payload)
                if index == 0:
                    (directory / "preview.png").write_bytes(preview_png(frame))
                sample = {
                    "index": index, "capture_seconds": elapsed, "file": name,
                    "sha256": hashlib.sha256(frame.bytes_payload).hexdigest(),
                    "minimum": minimum, "maximum": maximum,
                }
                report["samples"].append(sample)
                assert elapsed <= 5.05, "Single-shot capture exceeded the 5-second hard timeout budget."
                if interval:
                    await asyncio.sleep(interval)
            await driver.stop_preview()
            p95 = float(np.percentile([sample["capture_seconds"] for sample in report["samples"]], 95))
            report["capture_p95_seconds"] = p95
            assert p95 <= 2.55, "Project acceptance: p95 <= exposure + 2.5 s."
        finally:
            await driver.disconnect()
        report["status"] = "PASS"
    finally:
        report["elapsed_seconds"] = time.monotonic() - started
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        error = sys.exc_info()[1]
        if error is not None:
            report["error"] = str(error)
        (directory / "camera-bench.json").write_text(json.dumps(report, indent=2) + "\n")
