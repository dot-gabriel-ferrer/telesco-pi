"""Device orchestration service."""

from __future__ import annotations

import asyncio
import errno
import re
from datetime import datetime, timezone
from uuid import uuid4

from apps.backend.app.core.errors import AppError
from apps.backend.app.core.event_bus import EventBus
from libs.config.settings import Settings
from libs.devices.interfaces import BaseDriver, CameraDriver, DeviceOperationError, MountDriver
from libs.devices.imaging import preview_png
from libs.devices.nncam import NncamCameraDriver
from libs.devices.player_one import PlayerOneCameraDriver
from libs.devices.skywatcher import SkyWatcherUdpMountDriver
from libs.devices.models import CameraConfiguration, DeviceCommandResult, DeviceStatus, MountCoordinates, SimulatedFault, TrackingMode
from libs.devices.registry import DriverRegistry
from libs.devices.stubs import AZGo2MountDriverStub, PlayerOneMarsMCameraDriverStub
from libs.sessions.service import SessionService
from libs.storage.models import IndexedFile
from libs.storage.service import StorageService
from services.simulator.drivers import SimulatedCameraDriver, SimulatedMountDriver
from libs.diagnostics.logging import get_logger

logger = get_logger(__name__)


class DeviceService:
    """Central device access layer for API handlers."""

    def __init__(
        self,
        settings: Settings,
        registry: DriverRegistry,
        event_bus: EventBus,
        session_service: SessionService,
        storage_service: StorageService,
    ) -> None:
        self.settings = settings
        self.registry = registry
        self.event_bus = event_bus
        self.session_service = session_service
        self.storage_service = storage_service

    async def start(self) -> None:
        if self.settings.device_mode == "simulator":
            self.registry.register(SimulatedMountDriver(self.settings))
            self.registry.register(SimulatedCameraDriver(self.settings))
        elif self.settings.device_mode == "stub":
            self.registry.register(AZGo2MountDriverStub())
            self.registry.register(PlayerOneMarsMCameraDriverStub())
        else:
            mounts = {
                "simulated": lambda: SimulatedMountDriver(self.settings),
                "az_go2_stub": AZGo2MountDriverStub,
                "skywatcher_udp": lambda: SkyWatcherUdpMountDriver(self.settings),
            }
            cameras = {
                "simulated": lambda: SimulatedCameraDriver(self.settings),
                "player_one_mars_m_stub": PlayerOneMarsMCameraDriverStub,
                "nncam": lambda: NncamCameraDriver(self.settings),
                "player_one": lambda: PlayerOneCameraDriver(self.settings),
            }
            self.registry.register(mounts[self.settings.mount_driver]())
            self.registry.register(cameras[self.settings.camera_driver]())

    async def stop(self) -> None:
        errors: list[DeviceOperationError] = []
        for driver in self.registry.values():
            try:
                await driver.disconnect()
            except DeviceOperationError as exc:
                logger.error("Device shutdown failed: %s: %s", driver.device_id, exc.message)
                errors.append(exc)
        if errors:
            raise errors[0]

    def _driver(self, device_id: str) -> BaseDriver:
        try:
            return self.registry.get(device_id)
        except KeyError as exc:
            raise AppError("device_not_found", "Device not found.", status_code=404) from exc

    def _mount(self) -> MountDriver:
        driver = self._driver("mount.primary")
        if not isinstance(driver, MountDriver):
            raise AppError("driver_configuration", "Configured mount driver has an invalid type.", status_code=500)
        return driver

    def _camera(self) -> CameraDriver:
        driver = self._driver("camera.primary")
        if not isinstance(driver, CameraDriver):
            raise AppError("driver_configuration", "Configured camera driver has an invalid type.", status_code=500)
        return driver

    async def list_devices(self) -> list[DeviceStatus]:
        return [await driver.get_status() for driver in self.registry.values()]

    async def get_device(self, device_id: str) -> DeviceStatus:
        return await self._driver(device_id).get_status()

    async def connect_device(self, device_id: str) -> DeviceCommandResult:
        result = await self._driver(device_id).connect()
        await self.event_bus.publish("device.connected" if result.accepted else "device.command.rejected", device_id, {"accepted": result.accepted, "message": result.message})
        return result

    async def disconnect_device(self, device_id: str) -> DeviceCommandResult:
        result = await self._driver(device_id).disconnect()
        await self.event_bus.publish("device.disconnected", device_id, {"accepted": result.accepted, "message": result.message})
        return result

    async def inject_fault(self, device_id: str, fault: SimulatedFault) -> DeviceCommandResult:
        result = await self._driver(device_id).inject_fault(fault)
        await self.event_bus.publish("device.fault", device_id, {"mode": fault.mode, "message": fault.message})
        return result

    async def manual_slew(self, delta_azimuth: float, delta_altitude: float) -> DeviceCommandResult:
        try:
            result = await self._mount().manual_slew(delta_azimuth, delta_altitude)
        except DeviceOperationError as exc:
            raise AppError(exc.code, exc.message, status_code=409) from exc
        await self.event_bus.publish("mount.slew", "mount.primary", {"delta_azimuth": delta_azimuth, "delta_altitude": delta_altitude})
        return result

    async def goto(self, coordinates: MountCoordinates) -> DeviceCommandResult:
        try:
            result = await self._mount().goto(coordinates)
        except DeviceOperationError as exc:
            raise AppError(exc.code, exc.message, status_code=409) from exc
        await self.event_bus.publish("mount.goto", "mount.primary", coordinates.model_dump())
        return result

    async def stop_mount(self) -> DeviceCommandResult:
        result = await self._mount().stop()
        await self.event_bus.publish("mount.stop", "mount.primary", {"message": result.message})
        return result

    async def set_tracking_mode(self, mode: TrackingMode) -> DeviceCommandResult:
        try:
            result = await self._mount().set_tracking_mode(mode)
        except DeviceOperationError as exc:
            raise AppError(exc.code, exc.message, status_code=409) from exc
        await self.event_bus.publish("mount.tracking", "mount.primary", {"mode": mode.value})
        return result

    async def configure_camera(self, configuration: CameraConfiguration) -> DeviceCommandResult:
        try:
            result = await self._camera().configure(configuration)
        except DeviceOperationError as exc:
            raise AppError(exc.code, exc.message, status_code=409) from exc
        await self.event_bus.publish("camera.configured", "camera.primary", configuration.model_dump())
        return result

    async def start_preview(self) -> DeviceCommandResult:
        try:
            result = await self._camera().start_preview()
        except DeviceOperationError as exc:
            raise AppError(exc.code, exc.message, status_code=409) from exc
        await self.event_bus.publish("camera.preview.started", "camera.primary", {"message": result.message})
        return result

    async def stop_preview(self) -> DeviceCommandResult:
        result = await self._camera().stop_preview()
        await self.event_bus.publish("camera.preview.stopped", "camera.primary", {"message": result.message})
        return result

    async def preview_frame(self) -> bytes:
        camera = self._camera()
        status = await camera.get_status()
        if not status.metadata.get("preview_active"):
            raise AppError("preview_inactive", "Start camera preview first.", status_code=409)
        frame = await camera.capture_still()
        return await asyncio.to_thread(preview_png, frame)

    async def capture_still(self, *, session_id: str | None, name_prefix: str) -> tuple[IndexedFile, IndexedFile]:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", name_prefix):
            raise AppError("capture_name_invalid", "Capture prefix must contain 1–64 letters, numbers, underscores or hyphens.", status_code=422)
        target_session = session_id or (self.session_service.get_active_session().id if self.session_service.get_active_session() else None)
        if target_session is None:
            raise AppError("session_required", "An active session is required to capture still images.", status_code=409)
        session = self.session_service.get_session(target_session)
        if session is None or session.status != "active":
            raise AppError("session_not_active", "Capture requires an existing active session.", status_code=409)
        try:
            frame = await self._camera().capture_still()
        except DeviceOperationError as exc:
            raise AppError(exc.code, exc.message, status_code=409) from exc
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "_" + uuid4().hex[:8]
        capture_name = f"{name_prefix}_{timestamp}.{frame.format}"
        preview_name = f"{name_prefix}_{timestamp}_preview.png"
        preview = await asyncio.to_thread(preview_png, frame)
        try:
            layout = self.storage_service.ensure_session_layout(target_session)
            capture_relative = str((layout.captures_dir / capture_name).relative_to(self.storage_service.root_dir))
            preview_relative = str((layout.previews_dir / preview_name).relative_to(self.storage_service.root_dir))
            self.storage_service.write_bytes_atomic(capture_relative, frame.bytes_payload)
            self.storage_service.write_bytes_atomic(preview_relative, preview)
        except OSError as exc:
            logger.error("Capture storage failed: %s", exc)
            if exc.errno == errno.ENOSPC:
                raise AppError("storage_full", "Storage is full. Free space before capturing again.", status_code=507) from exc
            raise AppError("storage_write_failed", "Capture could not be written to storage.", status_code=500) from exc
        file_record = self.storage_service.index_file(
            session_id=target_session,
            kind="capture",
            relative_path=capture_relative,
            metadata=frame.metadata,
        )
        preview_record = self.storage_service.index_file(
            session_id=target_session,
            kind="preview",
            relative_path=preview_relative,
            metadata=frame.metadata,
        )
        await self.event_bus.publish(
            "camera.capture.completed",
            "camera.primary",
            {"session_id": target_session, "file_id": file_record.file_id, "preview_id": preview_record.file_id},
        )
        return file_record, preview_record
