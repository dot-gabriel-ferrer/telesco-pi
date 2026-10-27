import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile

import pytest

from infra.scripts import fetch_player_one_sdk as downloader


def archive_for_test(tmp_path, monkeypatch, unsafe=None):
    archive = tmp_path / "sdk.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        for name in (
            "license.txt", "include/PlayerOneCamera.h",
            "lib/x64/libPlayerOneCamera.so.3.10.1",
            "lib/arm64/libPlayerOneCamera.so.3.10.1",
        ):
            member = tarfile.TarInfo(f"vendor/{name}")
            member.size = 4
            bundle.addfile(member, io.BytesIO(b"test"))
        if unsafe:
            member = tarfile.TarInfo(unsafe)
            member.size = 4
            bundle.addfile(member, io.BytesIO(b"test"))
    config = tmp_path / "infra/configs"
    config.mkdir(parents=True)
    manifest = {
        "url": "https://player-one-astronomy.com/sdk.tar.gz",
        "directory": "vendor", "version": "3.10.1",
        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
    }
    (config / "player-one-sdk.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(downloader, "ROOT", tmp_path)
    return archive


def test_verified_extraction_and_no_overwrite(tmp_path, monkeypatch):
    archive_for_test(tmp_path, monkeypatch)
    result = downloader.fetch(tmp_path)
    assert result["version"] == "3.10.1"
    assert (tmp_path / "vendor/lib/arm64/libPlayerOneCamera.so.3.10.1").is_file()
    with pytest.raises(FileExistsError, match="already exists"):
        downloader.fetch(tmp_path)


def test_corrupted_archive_never_extracts(tmp_path, monkeypatch):
    archive = archive_for_test(tmp_path, monkeypatch)
    archive.write_bytes(archive.read_bytes() + b"corruption")
    with pytest.raises(ValueError, match="checksum"):
        downloader.fetch(tmp_path)
    assert not (tmp_path / "vendor").exists()


@pytest.mark.parametrize("unsafe", ["../outside", "/outside", "other/file"])
def test_unsafe_archive_never_extracts(tmp_path, monkeypatch, unsafe):
    archive_for_test(tmp_path, monkeypatch, unsafe=unsafe)
    with pytest.raises(ValueError, match="Unsafe"):
        downloader.fetch(tmp_path)
    assert not (tmp_path / "vendor").exists()


@pytest.mark.parametrize("official_host", [True, False])
def test_https_download_checks_final_host(tmp_path, monkeypatch, official_host):
    archive = archive_for_test(tmp_path, monkeypatch)
    payload = archive.read_bytes()
    archive.unlink()
    class Response(io.BytesIO):
        url = "https://player-one-astronomy.com/sdk.tar.gz" if official_host else "https://unexpected.example/sdk.tar.gz"
    monkeypatch.setattr("urllib.request.urlopen", lambda url, timeout: Response(payload))
    if official_host:
        assert downloader.fetch(tmp_path)["version"] == "3.10.1"
    else:
        with pytest.raises(ValueError, match="outside"):
            downloader.fetch(tmp_path)
        assert not archive.exists()
        assert not (tmp_path / "vendor").exists()


def test_official_archive_when_available(tmp_path):
    root = Path(__file__).resolve().parents[2]
    archive = root / ".local-sdk/player-one/PlayerOne_Camera_SDK_Linux_V3.10.1.tar.gz"
    if not archive.is_file():
        pytest.skip("Optional extraction verification requires the downloaded vendor archive.")
    shutil.copyfile(archive, tmp_path / archive.name)
    result = downloader.fetch(tmp_path)
    assert result["sha256"] == "d683a7a793846b35c5de82f7cfab9e7a12a911f0b99f9e5dbf653ba0300f2886"
    assert (Path(result["sdk_root"]) / "license.txt").is_file()
