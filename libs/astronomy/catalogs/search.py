"""Catalog search with fuzzy name matching, coordinate filtering, and visibility helpers."""

from __future__ import annotations

import difflib
import logging
from math import acos, cos, radians, sin, degrees

from libs.astronomy.domain.constraints import ObservingConstraints
from libs.astronomy.domain.observer import ObserverLocation
from libs.astronomy.domain.targets import Target, TargetKind
from libs.astronomy.visibility.ephemeris import EphemerisCalculator

logger = logging.getLogger(__name__)


class CatalogSearch:
    def __init__(self, targets: list[Target]) -> None:
        self.targets = list(targets)

    def search(self, query: str, catalog_types: list[TargetKind] | None = None, max_results: int = 10) -> list[Target]:
        filtered = self.filter_by_kind(catalog_types) if catalog_types else list(self.targets)
        if not query.strip():
            return filtered[:max_results]
        names = {target.name: target for target in filtered}
        close = difflib.get_close_matches(query, list(names), n=max_results, cutoff=0.2)
        direct = [
            target for target in filtered
            if query.lower() in target.name.lower() or query.lower() in target.id.lower()
        ]
        merged: list[Target] = []
        seen: set[str] = set()
        for target in direct + [names[name] for name in close]:
            if target.id not in seen:
                merged.append(target)
                seen.add(target.id)
        return merged[:max_results]

    def search_by_coords(self, ra: float, dec: float, radius_deg: float) -> list[Target]:
        results: list[Target] = []
        for target in self.targets:
            if target.ra_deg is None or target.dec_deg is None:
                continue
            sep = self._angular_separation_deg(ra, dec, target.ra_deg, target.dec_deg)
            if sep <= radius_deg:
                results.append(target)
        return results

    def filter_by_kind(self, kinds: list[TargetKind] | None) -> list[Target]:
        if not kinds:
            return list(self.targets)
        allowed = set(kinds)
        return [target for target in self.targets if target.kind in allowed]

    def filter_by_magnitude(self, max_magnitude: float) -> list[Target]:
        return [target for target in self.targets if target.magnitude is not None and target.magnitude <= max_magnitude]

    def filter_by_visibility(self, observer: ObserverLocation, time_utc, constraints: ObservingConstraints) -> list[Target]:
        ephemeris = EphemerisCalculator()
        visible: list[Target] = []
        for target in self.targets:
            try:
                alt_deg, az_deg, airmass = ephemeris.get_altaz(target, observer, time_utc)
            except ValueError:
                continue
            if alt_deg < constraints.min_alt_deg:
                continue
            if constraints.max_airmass is not None and airmass is not None and airmass > constraints.max_airmass:
                continue
            if alt_deg < constraints.horizon_mask.min_altitude_for_azimuth(az_deg):
                continue
            visible.append(target)
        return visible

    @staticmethod
    def _angular_separation_deg(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
        ra1r, dec1r, ra2r, dec2r = map(radians, (ra1, dec1, ra2, dec2))
        cos_sep = sin(dec1r) * sin(dec2r) + cos(dec1r) * cos(dec2r) * cos(ra1r - ra2r)
        return degrees(acos(max(-1.0, min(1.0, cos_sep))))
