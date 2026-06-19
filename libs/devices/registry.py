"""Driver registry."""

from __future__ import annotations

from libs.devices.interfaces import BaseDriver


class DriverRegistry:
    """Simple in-memory driver registry."""

    def __init__(self) -> None:
        self._drivers: dict[str, BaseDriver] = {}

    def register(self, driver: BaseDriver) -> None:
        self._drivers[driver.device_id] = driver

    def get(self, device_id: str) -> BaseDriver:
        return self._drivers[device_id]

    def values(self) -> list[BaseDriver]:
        return list(self._drivers.values())

