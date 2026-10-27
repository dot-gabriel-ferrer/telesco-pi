import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("installer", ROOT / "install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


def release(tmp_path):
    data = {
        "telesco_pi-0.2.0-py3-none-any.whl": b"test wheel",
        "install.py": b"test installer",
        "constraints.txt": b"test constraints",
    }
    for name, value in data.items():
        (tmp_path / name).write_bytes(value)
    (tmp_path / "SHA256SUMS.json").write_text(json.dumps({name: hashlib.sha256(value).hexdigest() for name, value in data.items()}))
    return tmp_path


def test_release_hashes_detect_corruption_and_escape(tmp_path):
    directory = release(tmp_path)
    assert installer.verify_release(directory).suffix == ".whl"
    wheel = next(directory.glob("*.whl"))
    wheel.write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="Checksum"):
        installer.verify_release(directory)
    manifest = directory / "SHA256SUMS.json"
    manifest.write_text(json.dumps({"../outside": "0" * 64}))
    with pytest.raises(ValueError, match="inválido"):
        installer.verify_release(directory)


def test_offline_wheels_must_be_verified(tmp_path):
    directory = release(tmp_path)
    (directory / "wheelhouse").mkdir()
    (directory / "wheelhouse/unverified.whl").write_bytes(b"not verified")
    with pytest.raises(ValueError, match="no verificada"):
        installer.verify_release(directory)


def test_atomic_activation_and_rollback_preserve_data(tmp_path, monkeypatch):
    monkeypatch.setattr("os.geteuid", lambda: 1000)
    releases = tmp_path / "releases"
    first, second = releases / "first", releases / "second"
    first.mkdir(parents=True)
    second.mkdir()
    (tmp_path / "data").mkdir()
    observation = tmp_path / "data/observation.png"
    observation.write_bytes(b"original")
    installer.atomic_link(first, tmp_path / "previous")
    installer.atomic_link(second, tmp_path / "current")
    assert installer.main(["--prefix", str(tmp_path), "--rollback", "--no-path-link"]) == 0
    assert (tmp_path / "current").resolve() == first
    assert (tmp_path / "previous").resolve() == second
    assert observation.read_bytes() == b"original"
    assert not (tmp_path / ".install-lock").exists()


def test_rollback_without_previous_does_not_change_current(tmp_path, monkeypatch):
    monkeypatch.setattr("os.geteuid", lambda: 1000)
    current = tmp_path / "releases/only"
    current.mkdir(parents=True)
    installer.atomic_link(current, tmp_path / "current")
    assert installer.main(["--prefix", str(tmp_path), "--rollback", "--no-path-link"]) == 1
    assert (tmp_path / "current").resolve() == current
