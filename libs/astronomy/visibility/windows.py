"""Visibility-window computation over sampled night intervals."""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta, timezone

from libs.astronomy.contracts.visibility import VisibilityWindow
from libs.astronomy.domain.constraints import ObservingConstraints
from libs.astronomy.domain.observer import ObserverLocation
from libs.astronomy.domain.targets import Target
from libs.astronomy.visibility.constraints import ConstraintEvaluator
from libs.astronomy.visibility.ephemeris import EphemerisCalculator

logger = logging.getLogger(__name__)


class VisibilityWindowCalculator:
    def __init__(self, sample_minutes: int = 10, ephemeris: EphemerisCalculator | None = None) -> None:
        self.sample_minutes = sample_minutes
        self.ephemeris = ephemeris or EphemerisCalculator()
        self.constraint_evaluator = ConstraintEvaluator(self.ephemeris)

    def compute_window(self, target: Target, observer: ObserverLocation, night_window, constraints: ObservingConstraints) -> VisibilityWindow:
        current = night_window.start_utc
        step = timedelta(minutes=self.sample_minutes)
        visible_times: list[tuple[datetime, float]] = []
        while current <= night_window.end_utc:
            ok, _ = self.constraint_evaluator.evaluate(target, observer, current, constraints)
            alt_deg, _, _ = self.ephemeris.get_altaz(target, observer, current)
            if ok:
                visible_times.append((current, alt_deg))
            current += step
        if not visible_times:
            return VisibilityWindow(is_visible=False)
        peak_time, peak_alt = max(visible_times, key=lambda item: item[1])
        return VisibilityWindow(
            start_utc=visible_times[0][0],
            end_utc=visible_times[-1][0],
            peak_alt_utc=peak_time,
            peak_alt_deg=float(peak_alt),
            is_visible=True,
        )

    def compute_night_window(self, observer: ObserverLocation, night_date: date) -> tuple[datetime, datetime]:
        start = datetime.combine(night_date, time(0, 0), tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        step = timedelta(minutes=10)
        dark_times: list[datetime] = []
        current = start
        while current <= end:
            sun_alt, _ = self.ephemeris.get_sun_altaz(observer, current)
            if sun_alt <= -18.0:
                dark_times.append(current)
            current += step
        if not dark_times:
            raise ValueError('Astronomical twilight not found for requested date and observer.')
        return dark_times[0], dark_times[-1]
