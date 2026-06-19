"""SGP4 propagation wrappers for TLE-based tracking.

TLE accuracy degrades rapidly; LEO errors of roughly ~1 km/day are typical.
This implementation uses lightweight geometric transforms to remain fast on CI and small devices.
"""

from __future__ import annotations

import logging
from datetime import datetime
from math import atan2, cos, degrees, radians, sin, sqrt

from sgp4.api import Satrec, jday

from libs.astronomy.domain.observer import ObserverLocation
from libs.astronomy.orbital.tle import TLERecord

logger = logging.getLogger(__name__)


class OrbitalPropagator:
    _A_EARTH_KM = 6378.137
    _E2 = 6.69437999014e-3

    def _satrec(self, tle: TLERecord) -> Satrec:
        return Satrec.twoline2rv(tle.line1, tle.line2)

    def propagate(self, tle: TLERecord, time_utc: datetime) -> tuple[float, float, float]:
        x_ecef, y_ecef, z_ecef = self._ecef_position_km(tle, time_utc)
        return self._ecef_to_geodetic(x_ecef, y_ecef, z_ecef)

    def get_altaz(self, tle: TLERecord, observer_location: ObserverLocation, time_utc: datetime) -> tuple[float, float, float]:
        sx, sy, sz = self._ecef_position_km(tle, time_utc)
        ox, oy, oz = self._observer_ecef_km(observer_location)
        dx, dy, dz = sx - ox, sy - oy, sz - oz

        lat = radians(observer_location.lat_deg)
        lon = radians(observer_location.lon_deg)
        east = -sin(lon) * dx + cos(lon) * dy
        north = -sin(lat) * cos(lon) * dx - sin(lat) * sin(lon) * dy + cos(lat) * dz
        up = cos(lat) * cos(lon) * dx + cos(lat) * sin(lon) * dy + sin(lat) * dz
        range_km = sqrt(east * east + north * north + up * up)
        alt_deg = degrees(atan2(up, sqrt(east * east + north * north)))
        az_deg = (degrees(atan2(east, north)) + 360.0) % 360.0
        return alt_deg, az_deg, range_km

    def is_visible(self, tle: TLERecord, observer: ObserverLocation, time_utc: datetime, min_alt_deg: float = 10) -> bool:
        alt_deg, _, _ = self.get_altaz(tle, observer, time_utc)
        return alt_deg >= min_alt_deg

    def _ecef_position_km(self, tle: TLERecord, time_utc: datetime) -> tuple[float, float, float]:
        sat = self._satrec(tle)
        jd, fr = jday(time_utc.year, time_utc.month, time_utc.day, time_utc.hour, time_utc.minute, time_utc.second + time_utc.microsecond / 1e6)
        error_code, position_km, _ = sat.sgp4(jd, fr)
        if error_code != 0:
            raise ValueError(f'SGP4 propagation failed with error code {error_code}.')
        theta = self._gmst_radians(jd + fr)
        x_teme, y_teme, z_teme = position_km
        x_ecef = cos(theta) * x_teme + sin(theta) * y_teme
        y_ecef = -sin(theta) * x_teme + cos(theta) * y_teme
        return float(x_ecef), float(y_ecef), float(z_teme)

    def _observer_ecef_km(self, observer: ObserverLocation) -> tuple[float, float, float]:
        lat = radians(observer.lat_deg)
        lon = radians(observer.lon_deg)
        alt_km = observer.elevation_m / 1000.0
        n = self._A_EARTH_KM / sqrt(1 - self._E2 * sin(lat) ** 2)
        x = (n + alt_km) * cos(lat) * cos(lon)
        y = (n + alt_km) * cos(lat) * sin(lon)
        z = (n * (1 - self._E2) + alt_km) * sin(lat)
        return x, y, z

    def _ecef_to_geodetic(self, x: float, y: float, z: float) -> tuple[float, float, float]:
        lon = atan2(y, x)
        p = sqrt(x * x + y * y)
        lat = atan2(z, p * (1 - self._E2))
        alt = 0.0
        for _ in range(5):
            n = self._A_EARTH_KM / sqrt(1 - self._E2 * sin(lat) ** 2)
            alt = p / max(cos(lat), 1e-9) - n
            lat = atan2(z, p * (1 - self._E2 * n / (n + alt)))
        return degrees(lat), ((degrees(lon) + 540.0) % 360.0) - 180.0, alt

    def _gmst_radians(self, jd: float) -> float:
        t = (jd - 2451545.0) / 36525.0
        gmst_deg = 280.46061837 + 360.98564736629 * (jd - 2451545.0) + 0.000387933 * t * t - (t**3) / 38710000.0
        return radians(gmst_deg % 360.0)
