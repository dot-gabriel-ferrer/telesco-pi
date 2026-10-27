"""Verify an installed launcher and bundled UI using only simulated devices."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request


def smoke(launcher: Path) -> dict:
    launcher = launcher.resolve()
    with tempfile.TemporaryDirectory(prefix="telesco-pi-smoke-") as directory:
        root = Path(directory)
        config = root / "config.json"
        subprocess.run([str(launcher), "--config", str(config), "init"], check=True, cwd=root, capture_output=True, text=True)
        settings = json.loads(config.read_text())
        settings.update(data_dir=str(root / "data"), device_mode="simulator",
                        mount_motion_enabled=False, camera_driver="simulated", mount_driver="simulated")
        config.write_text(json.dumps(settings))
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        base = f"http://127.0.0.1:{port}"
        log_path = root / "server.log"
        with log_path.open("w") as log:
            process = subprocess.Popen([str(launcher), "--config", str(config), "serve", "--port", str(port)],
                                       cwd=root, stdout=log, stderr=subprocess.STDOUT,
                                       env={**os.environ, "TELESCO_PI_PORT": "invalid-ignored-by-local-launcher"})
        try:
            ready = False
            for _ in range(150):
                if process.poll() is not None:
                    raise RuntimeError(f"El servidor terminó antes de estar listo:\n{log_path.read_text()}")
                try:
                    with urllib.request.urlopen(base + "/api/v1/health/ready", timeout=1) as response:
                        ready = response.status == 200
                    if ready:
                        break
                except (urllib.error.URLError, TimeoutError):
                    time.sleep(.1)
            if not ready:
                raise RuntimeError(f"El servidor no respondió en 15 segundos:\n{log_path.read_text()}")

            def request(path: str, body: dict | None = None, post: bool = False):
                data = None if body is None else json.dumps(body).encode()
                req = urllib.request.Request(base + path, data=data, method="POST" if post else "GET",
                                             headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=10) as response:
                    payload = response.read()
                    return json.loads(payload) if "application/json" in response.headers["Content-Type"] else payload

            assert b"<html" in request("/")
            for path in ("/control", "/capture", "/plan", "/files", "/sw.js"):
                assert request(path)
            devices = request("/api/v1/devices")["items"]
            assert len(devices) == 2 and all(device["implementation"] == "simulator" for device in devices)
            for device in devices:
                assert request(f"/api/v1/devices/{device['device_id']}/connect", post=True)["accepted"]
            session = request("/api/v1/sessions", {"name": "Installed release smoke"}, post=True)["session"]
            assert request("/api/v1/devices/camera/preview/start", post=True)["accepted"]
            before = len(request("/api/v1/sessions/files")["items"])
            for _ in range(3):
                assert request("/api/v1/devices/camera/preview/frame").startswith(b"\x89PNG")
            assert len(request("/api/v1/sessions/files")["items"]) == before
            captures = []
            for _ in range(3):
                capture = request("/api/v1/devices/camera/capture", {"session_id": session["id"]}, post=True)
                original = request(f"/api/v1/sessions/files/{capture['file']['file_id']}/content")
                preview = request(f"/api/v1/sessions/files/{capture['preview']['file_id']}/content")
                assert original.startswith(b"P5") and preview.startswith(b"\x89PNG")
                captures.append({"file_id": capture["file"]["file_id"], "sha256": hashlib.sha256(original).hexdigest()})
            assert len({capture["file_id"] for capture in captures}) == 3
            processed = request("/api/v1/processing/planetary", {
                "session_id": session["id"], "file_ids": [capture["file_id"] for capture in captures],
                "profile": "balanced",
            }, post=True)
            assert processed["total_frames"] == 3 and processed["selected_frames"] == 1
            assert request(f"/api/v1/sessions/files/{processed['file']['file_id']}/content").startswith(b"\x89PNG")
            assert request(f"/api/v1/sessions/files/{processed['array']['file_id']}/content").startswith(b"\x93NUMPY")
            assert request("/api/v1/devices/mount/stop", post=True)["accepted"]
            assert request("/api/v1/devices/camera/preview/stop", post=True)["accepted"]
            catalog = request("/api/v1/astronomy/catalog/search?q=M31")
            assert catalog["items"], "Falta catálogo empaquetado."
            for device in devices:
                assert request(f"/api/v1/devices/{device['device_id']}/disconnect", post=True)["accepted"]
            return {"status": "PASS", "launcher": str(launcher), "devices": "simulator_only",
                    "bundled_ui_routes": 5, "preview_frames": 3, "captures": captures, "catalog": "PASS",
                    "planetary_processing": "PASS"}
        finally:
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    process.wait(timeout=5)
                    raise RuntimeError("El backend no cerró en 15 segundos.")
            if process.returncode != 0:
                raise RuntimeError(f"Cierre del servidor con código {process.returncode}:\n{log_path.read_text()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--launcher", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = smoke(args.launcher)
    payload = json.dumps(result, indent=2) + "\n"
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(payload)
    print(payload)
