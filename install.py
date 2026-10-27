#!/usr/bin/env python3
"""Install a local Telesco-Pi release into a versioned, unprivileged venv."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import subprocess
import sys
import tempfile
import uuid
import venv

ROOT = Path(__file__).resolve().parent


def run(command: list[str], **kwargs) -> None:
    subprocess.run(command, check=True, **kwargs)


def atomic_link(target: Path, link: Path) -> None:
    temporary = link.with_name(f".{link.name}-{uuid.uuid4().hex}")
    try:
        temporary.symlink_to(target)
        temporary.replace(link)
    finally:
        temporary.unlink(missing_ok=True)


def verify_release(directory: Path) -> Path:
    hashes = json.loads((directory / "SHA256SUMS.json").read_text())
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError("Manifiesto de release vacío o inválido.")
    for name, digest in hashes.items():
        if not isinstance(name, str) or not isinstance(digest, str) or len(digest) != 64:
            raise ValueError("Entrada de checksum inválida.")
        path = (directory / name).resolve()
        if not path.is_relative_to(directory.resolve()) or not path.is_file():
            raise ValueError(f"Archivo de release inválido: {name}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"Checksum incorrecto: {name}")
    wheels = list(directory.glob("telesco_pi-*.whl"))
    if len(wheels) != 1 or wheels[0].name not in hashes:
        raise ValueError("La release debe contener exactamente una wheel verificada de Telesco-Pi.")
    if "install.py" not in hashes or "constraints.txt" not in hashes:
        raise ValueError("Falta instalador o constraints verificados.")
    if (directory / "wheelhouse").is_dir():
        for path in (directory / "wheelhouse").iterdir():
            if not path.is_file() or path.suffix != ".whl" or str(path.relative_to(directory)) not in hashes:
                raise ValueError(f"Wheel offline no verificada: {path.name}")
    return wheels[0]


def install(args: argparse.Namespace) -> None:
    if platform.system() != "Linux" or platform.machine().lower() not in ("x86_64", "amd64", "aarch64", "arm64"):
        raise ValueError("Se necesita Linux de 64 bits x64 o ARM64.")
    if not (3, 11) <= sys.version_info[:2] < (3, 14):
        raise ValueError("Usa Python 3.11–3.13 (por ejemplo python3.11 install.py).")
    if os.geteuid() == 0:
        raise ValueError("No ejecutar este instalador ni el backend como root.")
    prefix = args.prefix.expanduser().resolve()
    prefix.mkdir(parents=True, exist_ok=True)
    lock = prefix / ".install-lock"
    lock.mkdir()
    try:
        current, previous = prefix / "current", prefix / "previous"
        if args.rollback:
            if not current.is_symlink() or not previous.is_symlink():
                raise ValueError("No hay dos versiones instaladas para rollback.")
            old, restored = current.resolve(), previous.resolve()
            releases = prefix / "releases"
            if not old.is_relative_to(releases) or not restored.is_relative_to(releases) or not restored.is_dir():
                raise ValueError("Enlaces de versión fuera de releases o destino ausente.")
            atomic_link(restored, current)
            atomic_link(old, previous)
            print(f"Rollback completado: {restored}. Reinicia el proceso manualmente.")
            return
        directory = ROOT
        if (ROOT / "pyproject.toml").is_file():
            if args.offline:
                raise ValueError("Para offline, usa una release con wheelhouse; no el árbol de fuentes.")
            build_output = ROOT / ".release" / f"install-{uuid.uuid4().hex[:12]}"
            run([sys.executable, str(ROOT / "infra/scripts/build_release.py"), "--output", str(build_output)], cwd=ROOT)
            directory = build_output / "telesco-pi"
        wheel = verify_release(directory)
        if args.offline and not (directory / "wheelhouse").is_dir():
            raise ValueError("Esta release no contiene wheelhouse offline para este Python/arquitectura.")
        if current.exists() and not current.is_symlink():
            raise ValueError(f"{current} no es un enlace de instalación; no se sobrescribe.")
        releases = prefix / "releases"
        releases.mkdir(exist_ok=True)
        release = releases / f"{wheel.name.split('-')[1]}-{uuid.uuid4().hex[:12]}"
        # A failed version remains available for diagnosis, but is never activated.
        venv.EnvBuilder(with_pip=True).create(release)
        python = release / "bin/python"
        command = [str(python), "-m", "pip", "install", "--constraint", str(directory / "constraints.txt")]
        if args.offline:
            command += ["--no-index", "--find-links", str(directory / "wheelhouse")]
        run([*command, str(wheel)])
        run([str(python), "-m", "pip", "check"])
        run([str(python), "-I", "-c",
             "from pathlib import Path; import libs.cli; from libs.astronomy.catalogs.loaders import MessierLoader;"
             "assert MessierLoader().load(); assert (Path(libs.cli.__file__).parent/'webui/static/index.html').is_file()"])
        config = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "telesco-pi/config.json"
        if not config.exists():
            run([str(release / "bin/telesco-pi"), "init"])
        launcher = prefix / "bin/telesco-pi"
        launcher.parent.mkdir(exist_ok=True)
        content = f'#!/bin/sh\nexec {shlex.quote(str(current / "bin/telesco-pi"))} "$@"\n'
        with tempfile.NamedTemporaryFile(mode="w", dir=launcher.parent, delete=False) as temporary:
            temporary.write(content)
            temporary_path = Path(temporary.name)
        temporary_path.chmod(0o755)
        temporary_path.replace(launcher)
        external = None
        if not args.no_path_link:
            bin_dir = args.bin_dir.expanduser()
            bin_dir.mkdir(parents=True, exist_ok=True)
            external = bin_dir / "telesco-pi"
            if external.exists() or external.is_symlink():
                if not external.is_symlink() or external.resolve() != launcher.resolve():
                    raise ValueError(f"Ya existe {external} y no pertenece a esta instalación.")
        if current.is_symlink():
            old = current.resolve()
            if not old.is_relative_to(releases):
                raise ValueError("La versión actual apunta fuera de releases.")
            atomic_link(old, previous)
        atomic_link(release, current)
        if external is not None:
            atomic_link(launcher, external)
        print(f"\nInstalado: {launcher}\nConfig: {config}\nIniciar: {launcher} serve\nDiagnóstico: {launcher} doctor")
        print("No se han iniciado servicios, conectado dispositivos ni modificado permisos USB.")
    finally:
        lock.rmdir()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", type=Path, default=Path.home() / ".local/share/telesco-pi")
    parser.add_argument("--bin-dir", type=Path, default=Path.home() / ".local/bin")
    parser.add_argument("--no-path-link", action="store_true")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--rollback", action="store_true")
    args = parser.parse_args(argv)
    try:
        install(args)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Instalación fallida: {exc}. La versión previa no se elimina.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
