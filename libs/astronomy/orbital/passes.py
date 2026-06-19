"""Visible-pass computation over sampled propagation intervals."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from libs.astronomy.contracts.orbital import OrbitalPass, TrackPoint
from libs.astronomy.domain.observer import ObserverLocation
from libs.astronomy.orbital.propagation import OrbitalPropagator
from libs.astronomy.orbital.tle import TLERecord
from libs.astronomy.visibility.ephemeris import EphemerisCalculator

logger = logging.getLogger(__name__)


class PassCalculator:
    def __init__(self) -> None:
        self.propagator = OrbitalPropagator()
        self.ephemeris = EphemerisCalculator()

    def compute_passes(self, tle: TLERecord, observer: ObserverLocation, start_utc: datetime, end_utc: datetime, min_alt_deg: float = 10) -> list[OrbitalPass]:
        step = timedelta(seconds=10)
        current = start_utc
        samples: list[tuple[datetime, float, float]] = []
        while current <= end_utc:
            try:
                alt_deg, az_deg, _ = self.propagator.get_altaz(tle, observer, current)
            except ValueError:
                current += step
                continue
            samples.append((current, alt_deg, az_deg))
            current += step
        passes: list[OrbitalPass] = []
        current_segment: list[tuple[datetime, float, float]] = []
        for sample in samples:
            if sample[1] >= min_alt_deg:
                current_segment.append(sample)
            elif current_segment:
                passes.append(self._segment_to_pass(tle, observer, current_segment))
                current_segment = []
        if current_segment:
            passes.append(self._segment_to_pass(tle, observer, current_segment))
        return passes

    def _segment_to_pass(self, tle: TLERecord, observer: ObserverLocation, segment: list[tuple[datetime, float, float]]) -> OrbitalPass:
        peak = max(segment, key=lambda item: item[1])
        stride = max(1, int(round(15 / 10)))
        track = [TrackPoint(utc=t, alt_deg=alt, az_deg=az) for t, alt, az in segment[::stride]]
        sun_alt, _ = self.ephemeris.get_sun_altaz(observer, peak[0])
        visibility_class = 'dark' if sun_alt < -18 else 'twilight' if sun_alt < -6 else 'daylight'
        warnings = []
        if peak[1] < 20:
            warnings.append('low_quality_pass')
        return OrbitalPass(
            object_id=tle.name,
            object_name=tle.name,
            tle_epoch_utc=tle.epoch_utc,
            tle_age_hours=tle.age_hours(peak[0]),
            pass_start_utc=segment[0][0],
            pass_peak_utc=peak[0],
            pass_end_utc=segment[-1][0],
            peak_alt_deg=peak[1],
            az_alt_track=track,
            visibility_class=visibility_class,
            tracking_warnings=warnings,
            capture_window_recommendation='Use short exposures around peak altitude.' if peak[1] >= 20 else 'Pass is low; capture only if obstruction-free.',
            mount_command_rate_hz=1.0,
        )
