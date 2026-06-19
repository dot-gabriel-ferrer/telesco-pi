"""Observing constraints and local horizon-mask helpers."""

from __future__ import annotations

import logging
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class HorizonMask(BaseModel):
    azimuth_to_min_altitude: dict[int, float] = Field(default_factory=dict)

    def min_altitude_for_azimuth(self, azimuth_deg: float) -> float:
        if not self.azimuth_to_min_altitude:
            return 0.0
        bucket = int(round(azimuth_deg)) % 360
        return float(self.azimuth_to_min_altitude.get(bucket, 0.0))


class ObservingConstraints(BaseModel):
    min_alt_deg: float = 10.0
    max_airmass: float | None = None
    moon_sep_min_deg: float = 20.0
    horizon_mask: HorizonMask = Field(default_factory=HorizonMask)
