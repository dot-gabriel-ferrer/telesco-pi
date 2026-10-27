"""User installation entrypoint. Configuration changes never connect hardware."""

from __future__ import annotations

import argparse
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import tempfile

from pydantic import ValidationError
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

from libs.config.settings import Settings
from libs.devices.interfaces import DeviceOperationError
from libs.devices.player_one_sdk import probe


class LocalSettings(Settings):
    @classmethod
    def settings_customise_sources(
        cls, settings_cls: type[BaseSettings], init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource, dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (init_settings,)


def home_path(variable: str, suffix: str) -> Path:
    return Path(os.environ.get(variable, str(Path.home() / suffix))) / "telesco-pi"


def config_path() -> Path:
    return home_path("XDG_CONFIG_HOME", ".config") / "config.json"


def default_config() -> dict:
    return {
        "environment": "production",
        "data_dir": str(home_path("XDG_DATA_HOME", ".local/share") / "data"),
        "device_mode": "simulator", "camera_driver": "simulated",
        "mount_driver": "simulated", "mount_motion_enabled": False,
        "mount_max_step_deg": 0.1, "host": "127.0.0.1", "port": 8000,
    }


def read_config(path: Path) -> dict:
    if not path.is_file():
        raise ValueError(f"No existe configuración: {path}. Ejecuta 'telesco-pi init'.")
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("La configuración debe ser un objeto JSON.")
    unknown = set(data) - Settings.model_fields.keys()
    if unknown:
        raise ValueError(f"Opciones desconocidas: {', '.join(sorted(unknown))}")
    return data


def write_config(path: Path, data: dict) -> None:
    settings = LocalSettings(**data)
    if settings.host not in ("127.0.0.1", "localhost"):
        raise ValueError("El lanzador local solo admite loopback; para LAN usa un proxy TLS autenticado.")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(json.dumps(data, indent=2) + "\n")
        temporary_path.replace(path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def usb_devices() -> list[dict]:
    devices = []
    for path in sorted(Path("/sys/bus/usb/devices").glob("*")):
        if not (path / "idVendor").is_file() or (path / "idVendor").read_text().strip() != "a0a0":
            continue
        node = Path(f"/dev/bus/usb/{int((path / 'busnum').read_text()):03}/{int((path / 'devnum').read_text()):03}")
        devices.append({
            "vendor": "a0a0", "product_id": (path / "idProduct").read_text().strip(),
            "product": (path / "product").read_text().strip() if (path / "product").exists() else None,
            "node": str(node), "read_write_access": os.access(node, os.R_OK | os.W_OK),
        })
    return devices


def doctor(data: dict, sdk_probe: bool = False) -> dict:
    settings = LocalSettings(**data)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    checks = [
        {"name": "platform", "ok": platform.system() == "Linux" and platform.machine().lower() in ("aarch64", "arm64", "x86_64", "amd64"),
         "detail": f"{platform.system()} {platform.machine()} Python {platform.python_version()}"},
        {"name": "disk", "ok": shutil.disk_usage(settings.data_dir).free >= 2 * 1024**3,
         "detail": f"{shutil.disk_usage(settings.data_dir).free} bytes libres"},
        {"name": "loopback", "ok": settings.host in ("127.0.0.1", "localhost"), "detail": settings.host},
        {"name": "motion_disabled", "ok": not settings.mount_motion_enabled,
         "detail": "La habilitación de motores necesita operador presencial."},
    ]
    devices = usb_devices()
    if settings.camera_driver == "player_one":
        checks.append({"name": "usb_permissions", "ok": bool(devices) and all(device["read_write_access"] for device in devices),
                       "detail": devices})
        if sdk_probe:
            try:
                if settings.player_one_sdk_root is None:
                    raise ValueError("Falta player_one_sdk_root; ejecuta sdk-install y configure.")
                result = probe(settings.player_one_sdk_root)
                matching = [camera for camera in result["cameras"] if settings.camera_id in (camera["serial"], str(camera["camera_id"]))]
                checks.append({"name": "sdk", "ok": len(matching) == 1, "detail": result})
            except (DeviceOperationError, ValueError) as exc:
                checks.append({"name": "sdk", "ok": False, "detail": str(exc)})
    return {"ok": all(check["ok"] for check in checks), "checks": checks, "operation": "no_open_no_exposure_no_mount_commands"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="telesco-pi", description="Telesco-Pi para Linux x64/ARM64; no conecta dispositivos al iniciar.")
    parser.add_argument("--version", action="version", version=version("telesco-pi"))
    parser.add_argument("--config", type=Path, default=config_path())
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Crear configuración en simulación, sin sobrescribir.")
    configure = commands.add_parser("configure", help="Cambiar drivers sin conectar hardware.")
    configure.add_argument("--simulator", action="store_true")
    configure.add_argument("--camera", choices=["simulated", "player_one", "nncam"])
    configure.add_argument("--mount", choices=["simulated", "skywatcher_udp"])
    configure.add_argument("--camera-id")
    configure.add_argument("--sdk-root", type=Path)
    configure.add_argument("--mount-host")
    serve = commands.add_parser("serve", help="Servir API y PWA en http://127.0.0.1:8000.")
    serve.add_argument("--port", type=int)
    diagnostics = commands.add_parser("doctor", help="Diagnóstico local de lectura, sin movimiento.")
    diagnostics.add_argument("--sdk-probe", action="store_true", help="Enumerar SDK sin abrir cámaras.")
    sdk = commands.add_parser("sdk-install", help="Descargar SDK oficial, sin instalar reglas USB.")
    sdk.add_argument("--destination", type=Path, default=home_path("XDG_DATA_HOME", ".local/share") / "sdk/player-one")
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            if args.config.exists():
                raise ValueError(f"Ya existe {args.config}; no se sobrescribe.")
            write_config(args.config, default_config())
            print(f"Configuración creada en {args.config}; modo simulador.")
            return 0
        if args.command == "sdk-install":
            from infra.scripts.fetch_player_one_sdk import fetch
            print(json.dumps(fetch(args.destination), indent=2))
            return 0
        data = read_config(args.config)
        if args.command == "configure":
            if args.simulator:
                data.update(device_mode="simulator", camera_driver="simulated", mount_driver="simulated")
            for name in ("camera", "mount"):
                value = getattr(args, name)
                if value:
                    data[f"{name}_driver"] = value
                    data["device_mode"] = "configured"
            for name in ("camera_id", "sdk_root", "mount_host"):
                value = getattr(args, name)
                if value is not None:
                    data["player_one_sdk_root" if name == "sdk_root" else name] = str(value)
            data["mount_motion_enabled"] = False
            write_config(args.config, data)
            print("Configuración guardada. Motores bloqueados; reinicia el proceso para aplicarla.")
        elif args.command == "doctor":
            result = doctor(data, args.sdk_probe)
            print(json.dumps(result, indent=2))
            return 0 if result["ok"] else 1
        elif args.command == "serve":
            if args.port is not None:
                data["port"] = args.port
            settings = LocalSettings(**data)
            if settings.host not in ("127.0.0.1", "localhost"):
                raise ValueError("El lanzador solo admite loopback. Consulta el despliegue TLS para LAN.")
            static_dir = Path(__file__).parent / "webui/static"
            if not (static_dir / "index.html").is_file():
                raise ValueError("Falta la interfaz empaquetada. Ejecuta el instalador o build_release.py.")
            settings.frontend_dir = static_dir
            import uvicorn
            from apps.backend.app.factory import create_app
            print(f"Telesco-Pi: http://{settings.host}:{settings.port} — Ctrl+C para cerrar.")
            uvicorn.run(create_app(settings), host=settings.host, port=settings.port)
        return 0
    except (OSError, ValueError, ValidationError, DeviceOperationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
