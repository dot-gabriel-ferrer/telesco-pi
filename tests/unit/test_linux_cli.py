import json
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from apps.backend.app.main import create_app
from libs import cli
from libs.config.settings import Settings
from libs.devices.imaging import preview_png
from libs.devices.models import CapturedFrame


def test_init_configure_and_environment_isolation(tmp_path, monkeypatch):
    config = tmp_path / "config.json"
    monkeypatch.setenv("TELESCO_PI_MOUNT_MOTION_ENABLED", "true")
    monkeypatch.setenv("TELESCO_PI_DEVICE_MODE", "configured")
    monkeypatch.setenv("TELESCO_PI_CAMERA_DRIVER", "player_one")
    assert cli.main(["--config", str(config), "init"]) == 0
    initial = json.loads(config.read_text())
    assert initial["device_mode"] == "simulator"
    assert initial["mount_motion_enabled"] is False
    assert cli.LocalSettings().mount_motion_enabled is False
    assert cli.LocalSettings().camera_driver == "simulated"
    assert cli.main(["--config", str(config), "init"]) == 1
    assert json.loads(config.read_text()) == initial
    assert cli.main(["--config", str(config), "configure", "--camera", "player_one",
                     "--camera-id", "TEST", "--sdk-root", str(tmp_path / "sdk")]) == 0
    data = cli.read_config(config)
    assert data["device_mode"] == "configured" and data["camera_driver"] == "player_one"
    assert data["camera_id"] == "TEST" and not data["mount_motion_enabled"]
    assert cli.main(["--config", str(config), "configure", "--simulator"]) == 0
    assert cli.read_config(config)["camera_driver"] == "simulated"
    assert config.stat().st_mode & 0o777 == 0o600


def test_invalid_config_and_nonlocal_bind_are_explicit(tmp_path):
    config = tmp_path / "config.json"
    assert cli.main(["--config", str(config), "doctor"]) == 1
    config.write_text('{"unknown_option": true}')
    assert cli.main(["--config", str(config), "doctor"]) == 1
    config.write_text("[]")
    assert cli.main(["--config", str(config), "doctor"]) == 1
    with pytest.raises(ValueError, match="loopback"):
        cli.write_config(config, {"host": "0.0.0.0"})
    assert config.read_text() == "[]"


def test_doctor_usb_permission_failure_is_not_success(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "usb_devices", lambda: [{"read_write_access": False}])
    monkeypatch.setattr("shutil.disk_usage", lambda path: SimpleNamespace(free=4 * 1024**3))
    result = cli.doctor({"data_dir": tmp_path, "camera_driver": "player_one", "device_mode": "configured"}, sdk_probe=True)
    assert result["ok"] is False
    assert [item["ok"] for item in result["checks"] if item["name"] in ("usb_permissions", "sdk")] == [False, False]


def test_bundled_ui_is_served_without_swallowing_api_or_files(tmp_path):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<html>Telesco-Pi</html>")
    (tmp_path / "private.txt").write_text("private")
    with TestClient(create_app(Settings(environment="test", data_dir=tmp_path / "data", frontend_dir=static))) as client:
        assert client.get("/").text == "<html>Telesco-Pi</html>"
        assert client.get("/control").text == "<html>Telesco-Pi</html>"
        assert client.get("/capture").headers["cache-control"] == "no-cache"
        assert client.get("/api/v1/health/ready").status_code == 200
        assert client.get("/api/v1/not-found").status_code == 404
        assert client.get("/private.txt").status_code == 404
        assert client.get("/%2e%2e/private.txt").status_code == 404


def test_local_api_rejects_foreign_host_and_browser_origin(tmp_path):
    with TestClient(create_app(Settings(environment="test", data_dir=tmp_path))) as client:
        response = client.post("/api/v1/devices/camera.primary/connect", headers={"Origin": "https://untrusted.example"})
        assert response.status_code == 403
        assert response.json()["code"] == "origin_not_allowed"
        devices = client.get("/api/v1/devices").json()["items"]
        assert all(device["connection_state"] == "disconnected" for device in devices)
        assert client.get("/api/v1/health/ready", headers={"Host": "untrusted.example"}).status_code == 400
        assert client.post("/api/v1/devices/camera.primary/connect", headers={"Origin": "http://testserver"}).json()["accepted"]
        assert client.get("/api/v1/health/ready", headers={"Origin": "http://localhost:5173"}).status_code == 200
        from starlette.websockets import WebSocketDisconnect
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/api/v1/ws/events", headers={"Origin": "https://untrusted.example"}):
                pytest.fail("A foreign browser origin must not receive events.")


@pytest.mark.parametrize("pattern,red", [
    ("RGGB", (0, 0)), ("BGGR", (1, 1)), ("GRBG", (0, 1)), ("GBRG", (1, 0)),
])
def test_bayer_preview_channel_order(pattern, red):
    image = np.zeros((8, 8), np.uint16)
    image[red[0]::2, red[1]::2] = 65535
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    frame = CapturedFrame(format="png", bytes_payload=encoded.tobytes(), width=8, height=8, metadata={"bayer_pattern": pattern})
    preview = cv2.imdecode(np.frombuffer(preview_png(frame), np.uint8), cv2.IMREAD_UNCHANGED)
    assert np.all(preview[2:-2, 2:-2, 2] == 255)
    assert not np.any(preview[2:-2, 2:-2, :2])
