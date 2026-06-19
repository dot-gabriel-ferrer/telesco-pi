"""Observer and site metadata models with astropy conversion helpers."""

from __future__ import annotations

import logging
from pydantic import BaseModel, Field, model_validator
from astropy.coordinates import EarthLocation

logger = logging.getLogger(__name__)


class ObserverLocation(BaseModel):
    lat_deg: float
    lon_deg: float
    elevation_m: float = 0.0
    timezone_name: str = 'UTC'

    @model_validator(mode='after')
    def _validate_ranges(self) -> 'ObserverLocation':
        self.validate()
        return self

    def validate(self) -> None:
        if not -90.0 <= self.lat_deg <= 90.0:
            raise ValueError('Latitude must be between -90 and 90 degrees.')
        if not -180.0 <= self.lon_deg <= 180.0:
            raise ValueError('Longitude must be between -180 and 180 degrees.')

    def to_astropy_location(self) -> EarthLocation:
        return EarthLocation.from_geodetic(self.lon_deg, self.lat_deg, self.elevation_m)


class SiteProfile(BaseModel):
    name: str
    location: ObserverLocation
    horizon_mask: dict[int, float] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
