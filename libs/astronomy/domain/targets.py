"""Target models for fixed-sky, solar system, and orbital planning use cases."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Iterable

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TargetKind(str, Enum):
    PLANET = 'planet'
    MOON = 'moon'
    STAR = 'star'
    MESSIER = 'messier'
    NGC_IC = 'ngc_ic'
    COMET = 'comet'
    SATELLITE = 'satellite'
    CUSTOM = 'custom'


class SolarSystemBody(str, Enum):
    MERCURY = 'mercury'
    VENUS = 'venus'
    MARS = 'mars'
    JUPITER = 'jupiter'
    SATURN = 'saturn'
    URANUS = 'uranus'
    NEPTUNE = 'neptune'
    MOON = 'moon'
    SUN = 'sun'


class Target(BaseModel):
    id: str
    name: str
    kind: TargetKind
    ra_deg: float | None = None
    dec_deg: float | None = None
    magnitude: float | None = None
    constellation: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    angular_size_arcmin: float | None = None
    body: SolarSystemBody | None = None

    @property
    def requires_runtime_coordinates(self) -> bool:
        return self.body is not None


class TargetCatalog(BaseModel):
    targets: list[Target] = Field(default_factory=list)

    def add(self, target: Target) -> None:
        self.targets.append(target)

    def extend(self, targets: Iterable[Target]) -> None:
        self.targets.extend(targets)

    def get(self, target_id: str) -> Target | None:
        return next((target for target in self.targets if target.id == target_id), None)

    def search(self, query: str) -> list[Target]:
        needle = query.lower().strip()
        if not needle:
            return list(self.targets)
        return [
            target
            for target in self.targets
            if needle in target.id.lower() or needle in target.name.lower() or any(needle in tag.lower() for tag in target.tags)
        ]
