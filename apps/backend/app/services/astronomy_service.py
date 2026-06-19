"""Astronomy service: integrates the astronomy-core engine with the backend."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from libs.astronomy.catalogs.loaders import BrightStarLoader, MessierLoader, PlanetLoader
from libs.astronomy.catalogs.search import CatalogSearch
from libs.astronomy.catalogs.tle_store import TLEStore
from libs.astronomy.contracts.catalogs import CatalogObject, TLERecord as TLECatalogRecord
from libs.astronomy.contracts.orbital import OrbitalPass
from libs.astronomy.contracts.planning import (
    EquipmentSpec,
    ObserverSpec,
    PlannerConstraints,
    PlannerRequest,
    PlannerResponse,
    TargetRef,
    TimeWindow,
)
from libs.astronomy.contracts.visibility import TargetScore, VisibilityWindow
from libs.astronomy.domain.constraints import HorizonMask, ObservingConstraints
from libs.astronomy.domain.observer import ObserverLocation
from libs.astronomy.domain.targets import Target, TargetKind
from libs.astronomy.orbital.passes import PassCalculator
from libs.astronomy.orbital.tle import TLEParser
from libs.astronomy.planner.scheduler import NightScheduler
from libs.astronomy.visibility.ephemeris import EphemerisCalculator
from libs.astronomy.visibility.scoring import VisibilityScorer
from libs.astronomy.visibility.windows import VisibilityWindowCalculator
from libs.config.settings import Settings

logger = logging.getLogger(__name__)

_KIND_ALIASES: dict[str, TargetKind] = {
    "messier": TargetKind.MESSIER,
    "star": TargetKind.STAR,
    "planet": TargetKind.PLANET,
    "satellite": TargetKind.SATELLITE,
}


class AstronomyService:
    """Exposes astronomy engine capabilities to the FastAPI backend."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._catalog: list[Target] = []
        self._tle_store = TLEStore()
        self._scheduler = NightScheduler()
        self._ephemeris = EphemerisCalculator()
        self._scorer = VisibilityScorer(self._ephemeris)
        self._window_calculator = VisibilityWindowCalculator(ephemeris=self._ephemeris)
        self._pass_calculator = PassCalculator()

    def initialize(self) -> None:
        """Load embedded catalogs into memory."""
        targets: list[Target] = []
        for loader in (MessierLoader(), BrightStarLoader(), PlanetLoader()):
            try:
                targets.extend(loader.load())
            except Exception:
                logger.exception("Failed to load catalog from %s", type(loader).__name__)
        self._catalog = targets
        logger.info("AstronomyService initialized: %d catalog objects loaded.", len(self._catalog))

    # ------------------------------------------------------------------
    # Catalog
    # ------------------------------------------------------------------

    def search_catalog(
        self,
        query: str = "",
        kinds: list[str] | None = None,
        max_results: int = 20,
    ) -> list[CatalogObject]:
        mapped_kinds: list[TargetKind] | None = None
        if kinds:
            mapped_kinds = [_KIND_ALIASES[k] for k in kinds if k in _KIND_ALIASES]
        searcher = CatalogSearch(self._catalog)
        results = searcher.search(query, catalog_types=mapped_kinds, max_results=max_results)
        return [
            CatalogObject(
                id=t.id,
                name=t.name,
                kind=t.kind.value,
                ra_deg=t.ra_deg,
                dec_deg=t.dec_deg,
                magnitude=t.magnitude,
                metadata={},
            )
            for t in results
        ]

    # ------------------------------------------------------------------
    # Visibility
    # ------------------------------------------------------------------

    def compute_visibility(
        self,
        target_id: str,
        observer: dict[str, Any],
        night_window: dict[str, Any],
        constraints: dict[str, Any] | None = None,
    ) -> VisibilityWindow | None:
        target = self._find_target(target_id)
        if target is None:
            return None
        obs = ObserverLocation(
            lat_deg=observer["lat_deg"],
            lon_deg=observer["lon_deg"],
            elevation_m=observer.get("elevation_m", 0.0),
            timezone_name=observer.get("timezone_name", "UTC"),
        )
        c = constraints or {}
        obs_constraints = ObservingConstraints(
            min_alt_deg=c.get("min_alt_deg", 10.0),
            moon_sep_min_deg=c.get("moon_sep_min_deg", 20.0),
            horizon_mask=HorizonMask(azimuth_to_min_altitude={}),
        )
        tw = TimeWindow(
            start_utc=datetime.fromisoformat(night_window["start_utc"]) if isinstance(night_window["start_utc"], str) else night_window["start_utc"],
            end_utc=datetime.fromisoformat(night_window["end_utc"]) if isinstance(night_window["end_utc"], str) else night_window["end_utc"],
        )
        return self._window_calculator.compute_window(target, obs, tw, obs_constraints)

    def score_target(
        self,
        target_id: str,
        observer: dict[str, Any],
        time_utc: datetime,
        constraints: dict[str, Any] | None = None,
    ) -> TargetScore | None:
        target = self._find_target(target_id)
        if target is None:
            return None
        obs = ObserverLocation(
            lat_deg=observer["lat_deg"],
            lon_deg=observer["lon_deg"],
            elevation_m=observer.get("elevation_m", 0.0),
            timezone_name=observer.get("timezone_name", "UTC"),
        )
        c = constraints or {}
        obs_constraints = ObservingConstraints(
            min_alt_deg=c.get("min_alt_deg", 10.0),
            moon_sep_min_deg=c.get("moon_sep_min_deg", 20.0),
            horizon_mask=HorizonMask(azimuth_to_min_altitude={}),
        )
        equipment = EquipmentSpec(focal_length_mm=650.0, aperture_mm=130.0)
        return self._scorer.score_target(target, obs, time_utc, obs_constraints, equipment)

    # ------------------------------------------------------------------
    # Planner
    # ------------------------------------------------------------------

    def generate_plan(self, request: PlannerRequest) -> PlannerResponse:
        return self._scheduler.generate_plan(request)

    def build_planner_request(
        self,
        target_ids: list[str],
        observer: dict[str, Any],
        night_window: dict[str, Any],
        mode: str = "mixed",
        constraints: dict[str, Any] | None = None,
    ) -> PlannerRequest:
        c = constraints or {}
        refs: list[TargetRef] = []
        for tid in target_ids:
            target = self._find_target(tid)
            if target is not None:
                refs.append(TargetRef(id=target.id, kind=target.kind.value, ra_deg=target.ra_deg, dec_deg=target.dec_deg))
        tw_start = night_window["start_utc"]
        tw_end = night_window["end_utc"]
        if isinstance(tw_start, str):
            tw_start = datetime.fromisoformat(tw_start)
        if isinstance(tw_end, str):
            tw_end = datetime.fromisoformat(tw_end)
        return PlannerRequest(
            observer=ObserverSpec(
                lat_deg=observer["lat_deg"],
                lon_deg=observer["lon_deg"],
                elevation_m=observer.get("elevation_m", 0.0),
                timezone_name=observer.get("timezone_name", "UTC"),
            ),
            equipment=EquipmentSpec(focal_length_mm=650.0, aperture_mm=130.0),
            night_window=TimeWindow(start_utc=tw_start, end_utc=tw_end),
            targets=refs,
            constraints=PlannerConstraints(
                min_alt_deg=c.get("min_alt_deg", 10.0),
                moon_sep_min_deg=c.get("moon_sep_min_deg", 20.0),
            ),
            mode=mode,
        )

    # ------------------------------------------------------------------
    # Orbital
    # ------------------------------------------------------------------

    def list_tle_objects(self) -> list[TLECatalogRecord]:
        from pathlib import Path

        sample_path = Path(__file__).resolve().parents[4] / "libs" / "astronomy" / "catalogs" / "datasets" / "sample_tle.txt"
        if not sample_path.exists():
            return []
        parser = TLEParser()
        records = parser.parse_file(sample_path)
        now = datetime.now(timezone.utc)
        return [TLECatalogRecord(name=r.name, line1=r.line1, line2=r.line2, fetched_at_utc=now) for r in records]

    def compute_passes(
        self,
        tle_name: str,
        observer: dict[str, Any],
        start_utc: datetime,
        end_utc: datetime,
        min_alt_deg: float = 10.0,
    ) -> list[OrbitalPass]:
        from pathlib import Path

        sample_path = Path(__file__).resolve().parents[4] / "libs" / "astronomy" / "catalogs" / "datasets" / "sample_tle.txt"
        if not sample_path.exists():
            return []
        parser = TLEParser()
        records = {r.name: r for r in parser.parse_file(sample_path)}
        if tle_name not in records:
            return []
        tle = records[tle_name]
        obs = ObserverLocation(
            lat_deg=observer["lat_deg"],
            lon_deg=observer["lon_deg"],
            elevation_m=observer.get("elevation_m", 0.0),
            timezone_name=observer.get("timezone_name", "UTC"),
        )
        return self._pass_calculator.compute_passes(tle, obs, start_utc, end_utc, min_alt_deg)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_target(self, target_id: str) -> Target | None:
        for t in self._catalog:
            if t.id == target_id or t.name.lower() == target_id.lower():
                return t
        return None
