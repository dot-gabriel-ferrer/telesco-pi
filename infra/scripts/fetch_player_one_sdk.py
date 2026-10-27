"""Download the pinned vendor SDK locally; never install rules or execute samples."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import urllib.request


ROOT = Path(__file__).resolve().parents[2]


def fetch(destination: Path) -> dict[str, str]:
    manifest = json.loads((ROOT / "infra/configs/player-one-sdk.json").read_text())
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / manifest["directory"]
    archive = destination / Path(manifest["url"]).name
    if not archive.exists():
        with tempfile.NamedTemporaryFile(dir=destination, delete=False) as temporary:
            temporary_path = Path(temporary.name)
            try:
                with urllib.request.urlopen(manifest["url"], timeout=60) as response:
                    if not response.url.startswith("https://player-one-astronomy.com/"):
                        raise ValueError("SDK download redirected outside the official HTTPS host.")
                    shutil.copyfileobj(response, temporary)
                temporary.flush()
                digest = hashlib.sha256(temporary_path.read_bytes()).hexdigest()
                if digest != manifest["sha256"]:
                    raise ValueError("SDK checksum mismatch. Do not use this download.")
                temporary_path.replace(archive)
            finally:
                temporary_path.unlink(missing_ok=True)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != manifest["sha256"]:
        raise ValueError("Local SDK archive checksum mismatch; no extraction performed.")
    if target.exists():
        raise FileExistsError(f"SDK directory already exists: {target}. Use a fresh destination to avoid overwriting it.")
    with tempfile.TemporaryDirectory(dir=destination) as stage:
        with tarfile.open(archive, "r:gz") as bundle:
            members = bundle.getmembers()
            for member in members:
                path = Path(member.name)
                if not path.parts or path.is_absolute() or ".." in path.parts or path.parts[0] != manifest["directory"]:
                    raise ValueError("Unsafe SDK archive path.")
                if not (member.isfile() or member.isdir() or member.issym()):
                    raise ValueError("Unsupported SDK archive entry.")
                if member.issym():
                    link = Path(member.linkname)
                    if link.is_absolute() or ".." in link.parts or len(link.parts) != 1:
                        raise ValueError("Unsafe SDK library symlink.")
            bundle.extractall(stage, filter="data")
        extracted = Path(stage) / manifest["directory"]
        for required in (
            "license.txt", "include/PlayerOneCamera.h",
            "lib/arm64/libPlayerOneCamera.so.3.10.1",
            "lib/x64/libPlayerOneCamera.so.3.10.1",
        ):
            if not (extracted / required).is_file():
                raise ValueError(f"Incomplete SDK: {required}")
        extracted.replace(target)
    return {"sdk_root": str(target.resolve()), "version": manifest["version"], "sha256": digest}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=ROOT / ".local-sdk/player-one")
    args = parser.parse_args()
    try:
        print(json.dumps(fetch(args.destination), indent=2))
    except (OSError, ValueError, tarfile.TarError) as exc:
        parser.exit(1, f"SDK download failed: {exc}\n")
