"""Device orchestration service."""

from __future__ import annotations

from datetime import datetime, timezone

from apps.backend.app.core.errors import AppError
from apps.backend.app.core.event_bus import EventBus
from libs.config.settings import Settings
from libs.devices.interfaces import CameraDriver, DeviceOperationError, MountDriver
from libs.devices.models import CameraConfiguration, DeviceCommandResult, DeviceKind, DeviceStatus, MountCoordinates, SimulatedFault, TrackingMode
from libs.devices.registry import DriverRegistry
from libs.devices.stubs import AZGo2MountDriverStub, PlayerOneMarsMCameraDriverStub
from libs.sessions.service import SessionService
from libs.storage.models import IndexedFile
from libs.storage.service import StorageService
from services.simulator.drivers import SimulatedCameraDriver, SimulatedMountDriver


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
        else:
            self.registry.register(AZGo2MountDriverStub())
            self.registry.register(PlayerOneMarsMCameraDriverStub())

    async def stop(self) -> None:
        for driver in self.registry.values():
            await driver.disconnect()

    def _mount(self) -> MountDriver:
        return self.registry.get("mount.primary")  # type: ignore[return-value]

    def _camera(self) -> CameraDriver:
        return self.registry.get("camera.primary")  # type: ignore[return-value]

    async def list_devices(self) -> list[DeviceStatus]:
        return [await driver.get_status() for driver in self.registry.values()]

    async def get_device(self, device_id: str) -> DeviceStatus:
        return await self.registry.get(device_id).get_status()

    async def connect_device(self, device_id: str) -> DeviceCommandResult:
        result = await self.registry.get(device_id).connect()
        await self.event_bus.publish("device.connected", device_id, {"accepted": result.accepted, "message": result.message})
        return result

    async def disconnect_device(self, device_id: str) -> DeviceCommandResult:
        result = await self.registry.get(device_id).disconnect()
        await self.event_bus.publish("device.disconnected", device_id, {"accepted": result.accepted, "message": result.message})
        return result

    async def inject_fault(self, device_id: str, fault: SimulatedFault) -> DeviceCommandResult:
        result = await self.registry.get(device_id).inject_fault(fault)
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

    async def capture_still(self, *, session_id: str | None, name_prefix: str) -> tuple[IndexedFile, IndexedFile]:
        target_session = session_id or (self.session_service.get_active_session().id if self.session_service.get_active_session() else None)
        if target_session is None:
            raise AppError("session_required", "An active session is required to capture still images.", status_code=409)
        try:
            frame = await self._camera().capture_still()
        except DeviceOperationError as exc:
            raise AppError(exc.code, exc.message, status_code=409) from exc
        layout = self.storage_service.ensure_session_layout(target_session)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        capture_name = f"{name_prefix}_{timestamp}.{frame.format}"
        preview_name = f"{name_prefix}_{timestamp}_preview.{frame.format}"
        capture_relative = str((layout.captures_dir / capture_name).relative_to(self.storage_service.root_dir))
        preview_relative = str((layout.previews_dir / preview_name).relative_to(self.storage_service.root_dir))
        self.storage_service.write_bytes_atomic(capture_relative, frame.bytes_payload)
        self.storage_service.write_bytes_atomic(preview_relative, frame.bytes_payload)
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

