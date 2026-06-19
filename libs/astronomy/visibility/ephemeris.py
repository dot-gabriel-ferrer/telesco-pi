"""Astropy-based ephemeris helpers for Alt/Az coordinates and moon illumination.

Assumptions:
- Uses astropy built-in solar-system body support only.
- No external JPL kernels are required.
"""

from __future__ import annotations

import logging
import warnings
from datetime import datetime
from math import cos, radians

import astropy.units as u
from astropy.coordinates import AltAz, SkyCoord, get_body, get_sun, solar_system_ephemeris
from astropy.coordinates.baseframe import NonRotationTransformationWarning
from astropy.time import Time
from astropy.utils import iers

from libs.astronomy.domain.observer import ObserverLocation
from libs.astronomy.domain.targets import SolarSystemBody, Target

logger = logging.getLogger(__name__)
iers.conf.auto_download = False
solar_system_ephemeris.set('builtin')
warnings.filterwarnings('ignore', category=NonRotationTransformationWarning)


class EphemerisCalculator:
    def get_altaz(self, target: Target, observer: ObserverLocation, time_utc: datetime) -> tuple[float, float, float | None]:
        obstime = Time(time_utc)
        frame = AltAz(obstime=obstime, location=observer.to_astropy_location())
        if target.body is not None:
            coord = self._body_coord(target.body, obstime, observer)
        elif target.ra_deg is not None and target.dec_deg is not None:
            coord = SkyCoord(ra=target.ra_deg * u.deg, dec=target.dec_deg * u.deg, frame='icrs')
        else:
            raise ValueError(f'Target {target.id} has no fixed or runtime coordinates.')
        altaz = coord.transform_to(frame)
        alt_deg = float(altaz.alt.deg)
        az_deg = float(altaz.az.deg)
        zenith_deg = 90.0 - alt_deg
        airmass = None if alt_deg <= 0 else float(1 / max(0.1, cos(radians(zenith_deg))))
        return alt_deg, az_deg, airmass

    def get_sun_altaz(self, observer: ObserverLocation, time_utc: datetime) -> tuple[float, float]:
        obstime = Time(time_utc)
        frame = AltAz(obstime=obstime, location=observer.to_astropy_location())
        altaz = get_sun(obstime).transform_to(frame)
        return float(altaz.alt.deg), float(altaz.az.deg)

    def get_moon_altaz_and_illumination(self, observer: ObserverLocation, time_utc: datetime) -> tuple[float, float, float]:
        obstime = Time(time_utc)
        frame = AltAz(obstime=obstime, location=observer.to_astropy_location())
        moon = get_body('moon', obstime, location=observer.to_astropy_location())
        sun = get_sun(obstime)
        altaz = moon.transform_to(frame)
        separation = moon.separation(sun).deg
        illumination = (1 - cos(radians(separation))) / 2
        return float(altaz.alt.deg), float(altaz.az.deg), float(illumination)

    def _body_coord(self, body: SolarSystemBody, obstime: Time, observer: ObserverLocation) -> SkyCoord:
        if body == SolarSystemBody.SUN:
            return get_sun(obstime)
        if body == SolarSystemBody.MOON:
            return get_body('moon', obstime, location=observer.to_astropy_location())
        return get_body(body.value, obstime, location=observer.to_astropy_location())
