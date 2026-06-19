"""System status service."""

from __future__ import annotations

from apps.backend.app.api.schemas import StorageSummaryResponse, SystemStatusResponse
from apps.backend.app.core.container import AppContainer


class SystemService:
    """Builds consolidated system status payloads."""

    def __init__(self, container: AppContainer) -> None:
        self.container = container

    async def status(self) -> SystemStatusResponse:
        files = self.container.storage_service.list_files()
        return SystemStatusResponse(
            app_name=self.container.settings.app_name,
            version=self.container.settings.app_version,
            environment=self.container.settings.environment,
            status="ready" if self.container.readiness() else "degraded",
            active_session=self.container.session_service.get_active_session(),
            devices=await self.container.device_service.list_devices(),
            storage=StorageSummaryResponse(
                root_dir=str(self.container.storage_service.root_dir),
                retention_days=self.container.settings.retention_days,
                indexed_files=len(files),
            ),
            recent_events=self.container.event_bus.recent(),
        )

