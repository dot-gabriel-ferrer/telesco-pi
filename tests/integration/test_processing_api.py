import asyncio
import errno
import hashlib
import io
import threading

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from apps.backend.app.factory import create_app
from libs.config.settings import Settings
from libs.astronomy.contracts.common import QualityProfile
from apps.backend.app.core.errors import AppError


@pytest.fixture
def bench(tmp_path):
    with TestClient(create_app(Settings(environment="test", data_dir=tmp_path / "data"))) as client:
        session_id = client.post("/api/v1/sessions", json={"name": "Processing test"}).json()["session"]["id"]
        client.post("/api/v1/devices/camera.primary/connect")
        captures = [client.post("/api/v1/devices/camera/capture", json={"session_id": session_id}).json() for _ in range(4)]
        yield client, session_id, captures


def body(session_id, captures):
    return {"session_id": session_id, "file_ids": [capture["file"]["file_id"] for capture in captures]}


def test_planetary_flow_downloads_and_preserves_originals(bench):
    client, session_id, captures = bench
    before = {capture["file"]["file_id"]: hashlib.sha256(client.get(f"/api/v1/sessions/files/{capture['file']['file_id']}/content").content).hexdigest() for capture in captures}
    response = client.post("/api/v1/processing/planetary", json=body(session_id, captures))
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total_frames"] == 4 and data["selected_frames"] == 2
    assert data["file"]["kind"] == "processed"
    assert data["file"]["metadata"]["source_file_ids"] == list(before)
    original = client.get(f"/api/v1/sessions/files/{data['file']['file_id']}/content").content
    image = cv2.imdecode(np.frombuffer(original, np.uint8), cv2.IMREAD_UNCHANGED)
    assert image.shape == (480, 640) and image.dtype == np.uint16
    assert np.ptp(image) > 0
    array = np.load(io.BytesIO(client.get(f"/api/v1/sessions/files/{data['array']['file_id']}/content").content), allow_pickle=False)
    assert array.shape == image.shape and np.isfinite(array).all()
    preview = cv2.imdecode(np.frombuffer(client.get(f"/api/v1/sessions/files/{data['preview']['file_id']}/content").content, np.uint8), cv2.IMREAD_UNCHANGED)
    assert preview.dtype == np.uint8
    for file_id, checksum in before.items():
        assert hashlib.sha256(client.get(f"/api/v1/sessions/files/{file_id}/content").content).hexdigest() == checksum


def test_rejects_duplicate_preview_missing_and_other_session_inputs(bench):
    client, session_id, captures = bench
    first = captures[0]["file"]["file_id"]
    before = len(client.get("/api/v1/sessions/files").json()["items"])
    for ids in ([first, first], [first, "missing"], [first, captures[1]["preview"]["file_id"]]):
        assert client.post("/api/v1/processing/planetary", json={"session_id": session_id, "file_ids": ids}).status_code == 422
    other = client.post("/api/v1/sessions", json={"name": "Other"}).json()["session"]["id"]
    assert client.post("/api/v1/processing/planetary", json=body(other, captures)).status_code == 422
    assert len(client.get("/api/v1/sessions/files").json()["items"]) >= before
    client.post(f"/api/v1/sessions/{other}/close")
    assert client.post("/api/v1/processing/planetary", json=body(other, captures)).status_code == 409


def test_rejects_memory_configuration_mismatch_and_constant_frames(bench, monkeypatch):
    client, session_id, captures = bench
    service = client.app.state.container.processing_service
    monkeypatch.setattr(service, "MAX_INPUT_BYTES", 1)
    response = client.post("/api/v1/processing/planetary", json=body(session_id, captures))
    assert response.status_code == 422 and response.json()["code"] == "processing_memory"
    monkeypatch.setattr(service, "MAX_INPUT_BYTES", 32 * 1024**2)
    client.post("/api/v1/devices/camera/configure", json={"configuration": {"exposure_ms": 100}})
    changed = client.post("/api/v1/devices/camera/capture", json={"session_id": session_id}).json()
    response = client.post("/api/v1/processing/planetary", json=body(session_id, [captures[0], changed]))
    assert response.status_code == 422 and response.json()["code"] == "processing_mismatch"
    path = client.app.state.container.storage_service.indexed_file_path(captures[0]["file"]["file_id"])
    cv2.imwrite(str(path), np.zeros((480, 640), np.uint8))
    response = client.post("/api/v1/processing/planetary", json=body(session_id, captures))
    assert response.status_code == 422 and response.json()["code"] == "processing_signal"


def test_output_full_disk_is_explicit(bench, monkeypatch):
    client, session_id, captures = bench
    def full(*args, **kwargs):
        raise OSError(errno.ENOSPC, "Injected full disk")
    monkeypatch.setattr(client.app.state.container.storage_service, "write_bytes_atomic", full)
    response = client.post("/api/v1/processing/planetary", json=body(session_id, captures))
    assert response.status_code == 507 and response.json()["code"] == "storage_full"


def test_source_symlink_outside_storage_is_rejected(bench, tmp_path):
    client, session_id, captures = bench
    storage = client.app.state.container.storage_service
    original = storage.indexed_file_path(captures[0]["file"]["file_id"])
    external = tmp_path / "outside.png"
    external.write_bytes(original.read_bytes())
    original.unlink()
    original.symlink_to(external)
    response = client.post("/api/v1/processing/planetary", json=body(session_id, captures))
    assert response.status_code == 422 and response.json()["code"] == "processing_source"


def test_pixel_depth_mismatch_is_rejected(bench):
    client, session_id, captures = bench
    path = client.app.state.container.storage_service.indexed_file_path(captures[1]["file"]["file_id"])
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    ok, encoded = cv2.imencode(".png", image.astype(np.uint16) * 256)
    assert ok
    path.write_bytes(encoded.tobytes())
    response = client.post("/api/v1/processing/planetary", json=body(session_id, captures))
    assert response.status_code == 422 and response.json()["code"] == "processing_mismatch"


async def test_busy_rejection_and_cancellation_hold_worker_lock(bench, monkeypatch):
    client, session_id, captures = bench
    service = client.app.state.container.processing_service
    entered, release = threading.Event(), threading.Event()
    def blocked(*args):
        entered.set()
        release.wait(timeout=2)
        return {"status": "ok"}
    monkeypatch.setattr(service, "_planetary", blocked)
    ids = body(session_id, captures)["file_ids"]
    task = asyncio.create_task(service.planetary(session_id, ids, QualityProfile.BALANCED))
    try:
        for _ in range(100):
            if entered.is_set():
                break
            await asyncio.sleep(.005)
        assert entered.is_set()
        task.cancel()
        await asyncio.sleep(.02)
        with pytest.raises(AppError, match="Another processing"):
            await service.planetary(session_id, ids, QualityProfile.BALANCED)
        task.cancel()
        await asyncio.sleep(.02)
        assert service._lock.locked()
    finally:
        release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not service._lock.locked()
