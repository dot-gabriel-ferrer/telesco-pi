"""Embedded catalog loaders for Messier objects, bright stars, planets, and TLEs."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from libs.astronomy.catalogs.models import CatalogEntry, TLEEntry
from libs.astronomy.catalogs.tle_store import TLEStore
from libs.astronomy.domain.targets import SolarSystemBody, Target, TargetKind

logger = logging.getLogger(__name__)
DATASETS_DIR = Path(__file__).resolve().parent / 'datasets'


class _JsonLoader:
    dataset_name: str

    def _load_json(self) -> list[dict[str, object]]:
        path = DATASETS_DIR / self.dataset_name
        if not path.exists():
            raise FileNotFoundError(f'Embedded dataset not found: {path}')
        return json.loads(path.read_text(encoding='utf-8'))


class MessierLoader(_JsonLoader):
    dataset_name = 'messier.json'

    def load(self) -> list[Target]:
        rows = self._load_json()
        return [
            CatalogEntry(
                id=row['id'],
                name=row['name'],
                kind=TargetKind.MESSIER,
                ra_deg=row['ra_deg'],
                dec_deg=row['dec_deg'],
                magnitude=row['magnitude'],
                constellation=row['constellation'],
                description=row['description'],
                tags=[str(row['type']).lower().replace(' ', '_')],
                angular_size_arcmin=row['angular_size_arcmin'],
            ).to_target()
            for row in rows
        ]


class NGCLoader:
    """Placeholder NGC/IC loader returning an empty offline subset."""

    def load(self) -> list[Target]:
        logger.info('No embedded NGC/IC dataset shipped yet; returning empty list.')
        return []


class BrightStarLoader(_JsonLoader):
    dataset_name = 'bright_stars.json'

    def load(self) -> list[Target]:
        rows = self._load_json()
        results: list[Target] = []
        for row in rows:
            star_id = str(row['name']).lower().replace(' ', '_')
            results.append(
                CatalogEntry(
                    id=star_id,
                    name=row['name'],
                    kind=TargetKind.STAR,
                    ra_deg=row['ra_deg'],
                    dec_deg=row['dec_deg'],
                    magnitude=row['magnitude'],
                    constellation=row['constellation'],
                    description='Bright star from embedded offline subset.',
                    tags=['bright_star'],
                ).to_target()
            )
        return results


_BODY_MAP = {
    'mercury': SolarSystemBody.MERCURY,
    'venus': SolarSystemBody.VENUS,
    'mars': SolarSystemBody.MARS,
    'jupiter': SolarSystemBody.JUPITER,
    'saturn': SolarSystemBody.SATURN,
    'uranus': SolarSystemBody.URANUS,
    'neptune': SolarSystemBody.NEPTUNE,
    'moon': SolarSystemBody.MOON,
    'sun': SolarSystemBody.SUN,
}


class PlanetLoader(_JsonLoader):
    dataset_name = 'planets.json'

    def load(self) -> list[Target]:
        rows = self._load_json()
        targets: list[Target] = []
        for row in rows:
            kind = TargetKind.MOON if row['kind'] == 'moon' else TargetKind.PLANET
            mag_range = row.get('magnitude_range', [None, None])
            angular_range = row.get('angular_size_range_arcmin', [None, None])
            targets.append(
                Target(
                    id=str(row['id']),
                    name=str(row['name']),
                    kind=kind,
                    magnitude=float(mag_range[0]) if mag_range[0] is not None else None,
                    description=f"{row['best_season_notes']} {row['observation_notes']}",
                    tags=['runtime_coordinates'],
                    angular_size_arcmin=float(angular_range[1]) if angular_range[1] is not None else None,
                    body=_BODY_MAP[str(row['id'])],
                )
            )
        return targets


class TLELoader:
    def __init__(self, store: TLEStore | None = None) -> None:
        self.store = store or TLEStore()

    def load(self) -> list[Target]:
        targets: list[Target] = []
        for entry in self.store.get_all():
            targets.append(
                Target(
                    id=entry.name,
                    name=entry.name,
                    kind=TargetKind.SATELLITE,
                    description=f'TLE source: {entry.source}',
                    tags=['orbital', 'runtime_coordinates'],
                )
            )
        return targets

    def load_entries(self) -> list[TLEEntry]:
        return self.store.get_all()
