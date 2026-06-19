"""Heuristic target scoring for planning.

Scoring is empirical and intended for practical ranking, not optimal scheduling.
"""

from __future__ import annotations

import logging
from math import acos, cos, degrees, radians, sin

from libs.astronomy.contracts.planetary import FrameQuality
from libs.astronomy.contracts.visibility import ScoreContribution, TargetScore
from libs.astronomy.domain.constraints import ObservingConstraints
from libs.astronomy.domain.observer import ObserverLocation
from libs.astronomy.domain.targets import Target, TargetKind
from libs.astronomy.visibility.ephemeris import EphemerisCalculator

logger = logging.getLogger(__name__)


class VisibilityScorer:
    def __init__(self, ephemeris: EphemerisCalculator | None = None) -> None:
        self.ephemeris = ephemeris or EphemerisCalculator()

    def score_target(self, target: Target, observer: ObserverLocation, time_utc, constraints: ObservingConstraints, equipment) -> TargetScore:
        alt_deg, az_deg, airmass = self.ephemeris.get_altaz(target, observer, time_utc)
        moon_alt, moon_az, _ = self.ephemeris.get_moon_altaz_and_illumination(observer, time_utc)
        moon_sep = self._angular_sep_altaz(alt_deg, az_deg, moon_alt, moon_az)

        altitude_score = max(0.0, min(1.0, (alt_deg - constraints.min_alt_deg) / max(1.0, 90.0 - constraints.min_alt_deg)))
        airmass_score = 0.0 if airmass is None else max(0.0, min(1.0, 2.5 / max(1.0, airmass)))
        moon_sep_score = max(0.0, min(1.0, moon_sep / max(1.0, constraints.moon_sep_min_deg * 2)))
        magnitude_score = 0.7 if target.magnitude is None else max(0.0, min(1.0, (10 - target.magnitude) / 10))
        angular_size_score = 0.5 if target.angular_size_arcmin is None else max(0.0, min(1.0, target.angular_size_arcmin / 30.0))

        contributions = [
            ScoreContribution(name='altitude_score', score=altitude_score, weight=0.35, explanation='Higher altitude usually improves seeing and reduces extinction.'),
            ScoreContribution(name='airmass_score', score=airmass_score, weight=0.2, explanation='Lower airmass reduces atmospheric attenuation.'),
            ScoreContribution(name='moon_separation_score', score=moon_sep_score, weight=0.2, explanation='More lunar separation usually improves contrast.'),
            ScoreContribution(name='magnitude_score', score=magnitude_score, weight=0.15, explanation='Brighter targets are easier for compact systems.'),
            ScoreContribution(name='angular_size_score', score=angular_size_score, weight=0.1, explanation='Apparent size heuristically favors easier framing.'),
        ]
        total = sum(item.score * item.weight for item in contributions)
        if target.kind in {TargetKind.PLANET, TargetKind.MOON}:
            total = min(1.0, total + 0.05)
        return TargetScore(
            target_id=target.id,
            total_score=float(total),
            contributions=contributions,
            explanation='Heuristic score using altitude, airmass, moon separation, magnitude, and angular size.',
        )

    @staticmethod
    def _angular_sep_altaz(alt1: float, az1: float, alt2: float, az2: float) -> float:
        a1, z1, a2, z2 = map(radians, (alt1, az1, alt2, az2))
        cos_sep = sin(a1) * sin(a2) + cos(a1) * cos(a2) * cos(z1 - z2)
        return degrees(acos(max(-1.0, min(1.0, cos_sep))))
