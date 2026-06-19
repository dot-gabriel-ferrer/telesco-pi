from __future__ import annotations

from datetime import datetime, timezone

from libs.astronomy.domain.constraints import ObservingConstraints
from libs.astronomy.domain.observer import ObserverLocation
from libs.astronomy.domain.targets import Target, TargetKind
from libs.astronomy.visibility.ephemeris import EphemerisCalculator
from libs.astronomy.visibility.scoring import VisibilityScorer


def test_ephemeris_and_scoring() -> None:
    observer = ObserverLocation(lat_deg=40.416, lon_deg=-3.703, elevation_m=667)
    target = Target(id='M13', name='M13', kind=TargetKind.MESSIER, ra_deg=250.421, dec_deg=36.459, magnitude=5.8)
    when = datetime(2026, 7, 15, 23, 0, tzinfo=timezone.utc)
    ephemeris = EphemerisCalculator()
    alt, az, airmass = ephemeris.get_altaz(target, observer, when)
    assert -90 <= alt <= 90
    assert 0 <= az <= 360
    scorer = VisibilityScorer(ephemeris)
    score = scorer.score_target(target, observer, when, ObservingConstraints(), equipment={})
    assert 0 <= score.total_score <= 1
    assert len(score.contributions) == 5
