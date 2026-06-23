"""Application container."""

from __future__ import annotations

from dataclasses import dataclass

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from apps.backend.app.core.event_bus import EventBus
from apps.backend.app.db.session import create_database_engine, create_session_factory, initialize_database
from apps.backend.app.services.astronomy_service import AstronomyService
from apps.backend.app.services.device_service import DeviceService
from libs.config.settings import Settings
from libs.devices.registry import DriverRegistry
from libs.sessions.service import SessionService
from libs.storage.service import StorageService


@dataclass
class AppContainer:
    settings: Settings
    engine: Engine
    session_factory: sessionmaker[Session]
    event_bus: EventBus
    scheduler: AsyncIOScheduler
    storage_service: StorageService
    session_service: SessionService
    device_service: DeviceService
    astronomy_service: AstronomyService

    @classmethod
    def build(cls, settings: Settings) -> "AppContainer":
        engine = create_database_engine(settings)
        session_factory = create_session_factory(engine)
        event_bus = EventBus()
        scheduler = AsyncIOScheduler(timezone="UTC")
        storage_service = StorageService(settings, session_factory)
        session_service = SessionService(settings, session_factory, storage_service)
        registry = DriverRegistry()
        device_service = DeviceService(settings, registry, event_bus, session_service, storage_service)
        astronomy_service = AstronomyService(settings)
        return cls(
            settings=settings,
            engine=engine,
            session_factory=session_factory,
            event_bus=event_bus,
            scheduler=scheduler,
            storage_service=storage_service,
            session_service=session_service,
            device_service=device_service,
            astronomy_service=astronomy_service,
        )

    async def start(self) -> None:
        self.storage_service.ensure_runtime_directories()
        initialize_database(self.engine, self.settings)
        self.astronomy_service.initialize()
        await self.device_service.start()
        restored = self.session_service.restore_last_session()
        if restored:
            await self.event_bus.publish(
                "session.restored",
                "sessions",
                {"session_id": restored.id, "status": restored.status},
            )
        self.scheduler.add_job(self._heartbeat, "interval", seconds=self.settings.scheduler_heartbeat_seconds)
        self.scheduler.start()

    async def stop(self) -> None:
        self.scheduler.shutdown(wait=False)
        await self.device_service.stop()
        self.engine.dispose()

    async def _heartbeat(self) -> None:
        await self.event_bus.publish("system.heartbeat", "system", {"status": "alive"})

    def readiness(self) -> bool:
        return self.scheduler.running

