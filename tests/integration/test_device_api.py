import cv2
import errno
import numpy as np
import pytest
from fastapi.testclient import TestClient

from apps.backend.app.main import create_app
from libs.config.settings import Settings


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(Settings(environment="test", data_dir=tmp_path))) as client:
        yield client


def test_full_simulated_capture_flow(client):
    base = "/api/v1"
    status = client.get(f"{base}/system/status").json()
    assert len(status["devices"]) == 2
    assert status["devices"][0]["implementation"] == "simulator"
    assert client.post(f"{base}/devices/no-such-device/connect").status_code == 404
    assert client.post(f"{base}/devices/camera/capture", json={}).status_code == 409
    assert client.get(f"{base}/devices/camera/preview/frame").status_code == 409
    for device in ("mount.primary", "camera.primary"):
        assert client.post(f"{base}/devices/{device}/connect").json()["accepted"]
    session = client.post(f"{base}/sessions", json={"name": "Integration test"}).json()["session"]
    assert client.post(f"{base}/devices/mount/manual-slew", json={"delta_azimuth": 1, "delta_altitude": 0}).json()["accepted"]
    assert client.post(f"{base}/devices/mount/stop").json()["accepted"]
    assert client.post(f"{base}/devices/camera/configure", json={"configuration": {"exposure_ms": 20, "gain": 120}}).json()["accepted"]
    assert client.post(f"{base}/devices/camera/preview/start").json()["accepted"]
    before = client.get(f"{base}/sessions/files").json()["items"]
    for _ in range(2):
        frame = client.get(f"{base}/devices/camera/preview/frame")
        assert frame.status_code == 200
        assert frame.headers["content-type"] == "image/png"
        assert frame.headers["cache-control"] == "no-store"
        assert cv2.imdecode(np.frombuffer(frame.content, dtype=np.uint8), 0).shape == (480, 640)
    assert client.get(f"{base}/sessions/files").json()["items"] == before
    captures = [client.post(f"{base}/devices/camera/capture", json={"session_id": session["id"]}).json() for _ in range(2)]
    assert captures[0]["file"]["relative_path"] != captures[1]["file"]["relative_path"]
    preview = captures[0]["preview"]
    content = client.get(f'{base}/sessions/files/{preview["file_id"]}/content')
    assert content.status_code == 200 and content.content.startswith(b"\x89PNG")
    assert len(client.get(f'{base}/sessions/{session["id"]}/files').json()["items"]) == len(before) + 4
    assert client.post(f"{base}/devices/camera/preview/stop").json()["accepted"]
    assert client.get(f"{base}/devices/camera/preview/frame").status_code == 409
    assert client.get(f"{base}/sessions/files/nonexistent/content").status_code == 404


def test_invalid_commands_and_link_loss(client):
    base = "/api/v1/devices"
    assert client.post(f"{base}/camera.primary/connect").status_code == 200
    for prefix in ("../escape", "", "a/b", "a" * 65):
        assert client.post(f"{base}/camera/capture", json={"name_prefix": prefix}).status_code == 422
    assert client.post(f"{base}/camera/capture", json={"session_id": "../../escape"}).status_code == 409
    assert client.post(f"{base}/camera/configure", json={"configuration": {"exposure_ms": 0}}).status_code == 422
    assert client.post(f"{base}/mount/manual-slew", json={"delta_azimuth": 6, "delta_altitude": 0}).status_code == 422
    assert client.post(f"{base}/mount/manual-slew", json={"delta_azimuth": "NaN", "delta_altitude": 0}).status_code == 422
    response = client.post(
        f"{base}/mount/manual-slew", content='{"delta_azimuth": NaN, "delta_altitude": 0}',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    client.post(f"{base}/camera/preview/start")
    client.post(f"{base}/camera.primary/fault", json={"fault": {"mode": "disconnect"}})
    response = client.get(f"{base}/camera/preview/frame")
    assert response.status_code == 409
    assert response.json()["code"] == "simulated_camera_disconnect"


def test_configured_mode_does_not_fall_back_to_simulation(tmp_path):
    settings = Settings(
        environment="test", data_dir=tmp_path, device_mode="configured",
        camera_driver="nncam", camera_sdk_module="nonexistent_telesco_sdk",
    )
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/v1/devices/camera.primary/connect")
        assert response.status_code == 409
        assert response.json()["code"] == "camera_sdk_unavailable"
        camera = client.get("/api/v1/devices").json()["items"][1]
        assert camera["implementation"] == "real"
        assert camera["connection_state"] == "error"


def test_storage_full_is_reported_and_capture_not_announced(client, monkeypatch):
    client.post("/api/v1/sessions", json={"name": "Storage test"})
    client.post("/api/v1/devices/camera.primary/connect")
    storage = client.app.state.container.storage_service
    before = len(storage.list_files())
    def disk_full(*args, **kwargs):
        raise OSError(errno.ENOSPC, "No space left on device")
    monkeypatch.setattr(storage, "write_bytes_atomic", disk_full)
    response = client.post("/api/v1/devices/camera/capture", json={})
    assert response.status_code == 507
    assert response.json()["code"] == "storage_full"
    assert len(storage.list_files()) == before
    assert not any(event.event_type == "camera.capture.completed" for event in client.app.state.container.event_bus.recent())


def test_session_and_files_restore_without_reconnecting_hardware(tmp_path):
    settings = Settings(environment="test", data_dir=tmp_path)
    with TestClient(create_app(settings)) as client:
        session = client.post("/api/v1/sessions", json={"name": "Persistent session"}).json()["session"]
        client.post("/api/v1/devices/camera.primary/connect")
        capture = client.post("/api/v1/devices/camera/capture", json={}).json()
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/v1/sessions/active").json()["session"]["id"] == session["id"]
        assert client.get(f'/api/v1/sessions/files/{capture["file"]["file_id"]}/content').status_code == 200
        assert all(device["connection_state"] == "disconnected" for device in client.get("/api/v1/devices").json()["items"])


def test_download_does_not_follow_external_symlinks(client, tmp_path):
    storage = client.app.state.container.storage_service
    outside = tmp_path.parent / f"{tmp_path.name}-outside.txt"
    outside.write_text("not an observatory file")
    try:
        link = storage.root_dir / "external.txt"
        link.symlink_to(outside)
        record = storage.index_file(session_id=None, kind="test", relative_path="external.txt")
        assert client.get(f"/api/v1/sessions/files/{record.file_id}/content").status_code == 404
    finally:
        outside.unlink()


def test_night_planner_receives_session_and_request_context(client, monkeypatch):
    assert client.post("/api/v1/astronomy/plan", json={}).status_code == 409
    session = client.post("/api/v1/sessions", json={"name": "Planner test"}).json()["session"]
    service = client.app.state.container.astronomy_service
    original = service.generate_plan
    def generate(request):
        assert request.session_id == session["id"]
        assert request.request_id == "planner-context-test"
        return original(request)
    monkeypatch.setattr(service, "generate_plan", generate)
    targets = client.get("/api/v1/astronomy/catalog/search").json()["items"]
    response = client.post(
        "/api/v1/astronomy/plan", json={"targets": [targets[0]["id"]]},
        headers={"X-Request-ID": "planner-context-test"},
    )
    assert response.status_code == 200
    assert isinstance(response.json()["plan_items"], list)
    assert "diagnostics" in response.json()


def test_player_one_without_sdk_never_falls_back(tmp_path):
    settings = Settings(
        environment="test", data_dir=tmp_path, device_mode="configured",
        camera_driver="player_one", player_one_sdk_root=None,
    )
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/v1/devices/camera.primary/connect")
        assert response.status_code == 409
        assert response.json()["code"] == "player_one_sdk_unavailable"
        camera = client.get("/api/v1/devices").json()["items"][1]
        assert camera["implementation"] == "real"
        assert camera["connection_state"] == "error"
