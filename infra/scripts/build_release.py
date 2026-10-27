"""Build a Linux distribution with a bundled UI, checksums and optional offline wheels."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[2]


def run(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def frontend_notices() -> str:
    frontend = ROOT / "apps/frontend"
    lock = json.loads((frontend / "package-lock.json").read_text())
    notices = ["Frontend dependency notices; includes build-time dependencies for completeness.\n"]
    for name in sorted(lock["packages"]):
        if not name or not name.startswith("node_modules/"):
            continue
        directory = frontend / name
        package_file = directory / "package.json"
        if not package_file.is_file():
            continue
        package = json.loads(package_file.read_text())
        notices.append(f"\n--- {package.get('name', name)} {package.get('version', '')} ({package.get('license', 'see package')}) ---\n")
        for path in sorted(directory.iterdir()):
            if path.is_file() and path.name.lower().split(".")[0] in ("license", "licence", "copying"):
                notices.append(path.read_text(errors="replace") + "\n")
    return "".join(notices)


def build(output: Path, wheelhouse: bool = False) -> Path:
    output = output.resolve()
    destination = output / "telesco-pi"
    if destination.exists():
        raise FileExistsError(f"Ya existe {destination}. Usa --output con un directorio nuevo.")
    run(["npm", "ci"], ROOT / "apps/frontend")
    run(["npm", "run", "build"], ROOT / "apps/frontend")
    destination.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="telesco-pi-build-") as directory:
        stage = Path(directory)
        for name in ("libs", "services", "apps/backend"):
            shutil.copytree(ROOT / name, stage / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for name in ("pyproject.toml", "README.md", "LICENSE"):
            shutil.copyfile(ROOT / name, stage / name)
        (stage / "infra/scripts").mkdir(parents=True)
        (stage / "infra/configs").mkdir(parents=True)
        shutil.copyfile(ROOT / "infra/scripts/fetch_player_one_sdk.py", stage / "infra/scripts/fetch_player_one_sdk.py")
        shutil.copyfile(ROOT / "infra/configs/player-one-sdk.json", stage / "infra/configs/player-one-sdk.json")
        shutil.copytree(ROOT / "apps/frontend/dist", stage / "libs/webui/static")
        (stage / "libs/webui/static/THIRD_PARTY_NOTICES.txt").write_text(frontend_notices())
        run([sys.executable, "-m", "pip", "wheel", "--no-deps", "--wheel-dir", str(destination), "."], stage)
    shutil.copyfile(ROOT / "install.py", destination / "install.py")
    shutil.copyfile(ROOT / "LICENSE", destination / "LICENSE")
    shutil.copyfile(ROOT / "docs/deployment/linux-installer.md", destination / "INSTALL.md")
    shutil.copyfile(ROOT / "infra/configs/constraints.txt", destination / "constraints.txt")
    for folder in ("docs/deployment", "docs/testing", "docs/architecture", "infra/configs", "infra/systemd"):
        shutil.copytree(ROOT / folder, destination / folder)
    shutil.copyfile(ROOT / "README.md", destination / "README.md")
    (destination / "THIRD_PARTY_NOTICES.txt").write_text(frontend_notices())
    if wheelhouse:
        wheels = list(destination.glob("telesco_pi-*.whl"))
        if len(wheels) != 1:
            raise ValueError("Se esperaba exactamente una wheel de aplicación.")
        run([sys.executable, "-m", "pip", "download", "--only-binary=:all:",
             "--constraint", str(destination / "constraints.txt"), "--dest", str(destination / "wheelhouse"), str(wheels[0])], ROOT)
    metadata = {
        "version": tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"],
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()),
        "source_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for folder in ("libs", "apps/backend", "apps/frontend/src", "apps/frontend/public", "services", "infra/scripts", "infra/configs")
            for path in sorted((ROOT / folder).rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts and path.suffix not in (".pyc", ".log")
        },
        "build_inputs_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in ("pyproject.toml", "install.py", "apps/frontend/package.json", "apps/frontend/package-lock.json", "apps/frontend/vite.config.ts")
        },
        "offline": wheelhouse, "sdk_bundled": False,
        "build_architecture": platform.machine(), "build_python": platform.python_version(),
    }
    (destination / "BUILD.json").write_text(json.dumps(metadata, indent=2) + "\n")
    hashes = {
        str(path.relative_to(destination)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(destination.rglob("*")) if path.is_file()
    }
    (destination / "SHA256SUMS.json").write_text(json.dumps(hashes, indent=2) + "\n")
    variant = f"-{platform.machine()}-py{sys.version_info.major}{sys.version_info.minor}-offline" if wheelhouse else ""
    archive = output / f"telesco-pi-{metadata['version']}-linux{variant}.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        bundle.add(destination, arcname="telesco-pi")
    (archive.with_suffix(archive.suffix + ".sha256")).write_text(f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n")
    print(f"Release: {archive}")
    return archive


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / ".release")
    parser.add_argument("--wheelhouse", action="store_true", help="Dependencias offline solo para el Python/arquitectura de construcción.")
    args = parser.parse_args()
    try:
        build(args.output, args.wheelhouse)
    except (OSError, ValueError, subprocess.CalledProcessError, tarfile.TarError) as exc:
        parser.exit(1, f"No se pudo construir la release: {exc}\n")
