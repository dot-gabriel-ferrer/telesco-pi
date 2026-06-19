from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from libs.astronomy.domain.observer import ObserverLocation
from libs.astronomy.orbital.passes import PassCalculator
from libs.astronomy.orbital.propagation import OrbitalPropagator
from libs.astronomy.orbital.tle import TLEParser

ROOT = Path(__file__).resolve().parents[3]


def test_tle_parsing_and_propagation() -> None:
    records = TLEParser().parse_file(ROOT / 'libs/astronomy/testdata/tle/sample_tle.txt')
    iss = records[0]
    assert iss.name == 'ISS (ZARYA)'
    observer = ObserverLocation(lat_deg=40.416, lon_deg=-3.703, elevation_m=667)
    now = datetime(2026, 7, 15, 22, 0, tzinfo=timezone.utc)
    lat, lon, alt = OrbitalPropagator().propagate(iss, now)
    assert -90 <= lat <= 90
    assert -180 <= lon <= 180
    assert alt > 100


def test_pass_calculation() -> None:
    record = TLEParser().parse_file(ROOT / 'libs/astronomy/testdata/tle/sample_tle.txt')[0]
    observer = ObserverLocation(lat_deg=40.416, lon_deg=-3.703, elevation_m=667)
    start = datetime(2026, 7, 15, 20, 0, tzinfo=timezone.utc)
    end = start + timedelta(minutes=20)
    passes = PassCalculator().compute_passes(record, observer, start, end, min_alt_deg=-90)
    assert passes
