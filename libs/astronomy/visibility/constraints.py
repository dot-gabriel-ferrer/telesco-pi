"""Constraint evaluators for altitude, airmass, horizon, and lunar separation."""

from __future__ import annotations

import logging
from math import acos, cos, degrees, radians, sin

from libs.astronomy.domain.constraints import ObservingConstraints
from libs.astronomy.domain.observer import ObserverLocation
from libs.astronomy.domain.targets import Target
from libs.astronomy.visibility.ephemeris import EphemerisCalculator

logger = logging.getLogger(__name__)


class ConstraintEvaluator:
    def __init__(self, ephemeris: EphemerisCalculator | None = None) -> None:
        self.ephemeris = ephemeris or EphemerisCalculator()

    def evaluate(self, target: Target, observer: ObserverLocation, time_utc, constraints: ObservingConstraints) -> tuple[bool, list[str]]:
        reasons: list[str] = []
        alt_deg, az_deg, airmass = self.ephemeris.get_altaz(target, observer, time_utc)
        if alt_deg < constraints.min_alt_deg:
            reasons.append('below_min_altitude')
        if constraints.max_airmass is not None and airmass is not None and airmass > constraints.max_airmass:
            reasons.append('airmass_limit')
        if alt_deg < constraints.horizon_mask.min_altitude_for_azimuth(az_deg):
            reasons.append('horizon_mask')
        if constraints.moon_sep_min_deg > 0:
            moon_alt, moon_az, _ = self.ephemeris.get_moon_altaz_and_illumination(observer, time_utc)
            separation = self._angular_sep_altaz(alt_deg, az_deg, moon_alt, moon_az)
            if separation < constraints.moon_sep_min_deg:
                reasons.append('moon_separation')
        return not reasons, reasons

    @staticmethod
    def _angular_sep_altaz(alt1: float, az1: float, alt2: float, az2: float) -> float:
        a1, z1, a2, z2 = map(radians, (alt1, az1, alt2, az2))
        cos_sep = sin(a1) * sin(a2) + cos(a1) * cos(a2) * cos(z1 - z2)
        return degrees(acos(max(-1.0, min(1.0, cos_sep))))
