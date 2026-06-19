from __future__ import annotations

from pathlib import Path

from libs.astronomy.catalogs.loaders import BrightStarLoader, MessierLoader, PlanetLoader
from libs.astronomy.catalogs.search import CatalogSearch
from libs.astronomy.catalogs.tle_store import TLEStore
from libs.astronomy.domain.targets import TargetKind
from libs.astronomy.orbital.tle import TLEParser


ROOT = Path(__file__).resolve().parents[3]


def test_embedded_catalog_loaders() -> None:
    messier = MessierLoader().load()
    stars = BrightStarLoader().load()
    planets = PlanetLoader().load()
    assert len(messier) == 20
    assert any(target.id == 'M31' for target in messier)
    assert any(target.name == 'Sirius' for target in stars)
    assert any(target.id == 'jupiter' for target in planets)


def test_catalog_search() -> None:
    catalog = MessierLoader().load() + BrightStarLoader().load()
    search = CatalogSearch(catalog)
    results = search.search('andromeda', catalog_types=[TargetKind.MESSIER])
    assert results
    by_coords = search.search_by_coords(10.68, 41.26, radius_deg=2)
    assert any(target.id == 'M31' for target in by_coords)


def test_tle_store_and_parser_roundtrip(tmp_path: Path) -> None:
    sample = (ROOT / 'libs/astronomy/catalogs/datasets/sample_tle.txt').read_text(encoding='utf-8')
    parser = TLEParser()
    records = parser.parse_text(sample)
    assert len(records) == 3
    store = TLEStore()
    store.load_from_text(sample)
    cache_path = tmp_path / 'tle-cache.json'
    store.save(cache_path)
    loaded = TLEStore.load(cache_path)
    assert loaded.get('ISS (ZARYA)') is not None
