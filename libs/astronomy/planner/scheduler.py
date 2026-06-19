"""Night scheduler that combines visibility heuristics and orbital pass data."""

from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path

from libs.astronomy.catalogs.loaders import PlanetLoader
from libs.astronomy.contracts.planning import PlanItem as ContractPlanItem
from libs.astronomy.contracts.planning import PlannerDiagnostics, PlannerRequest, PlannerResponse, ScoreFactor
from libs.astronomy.domain.constraints import HorizonMask, ObservingConstraints
from libs.astronomy.domain.observer import ObserverLocation
from libs.astronomy.domain.targets import Target, TargetKind
from libs.astronomy.orbital.passes import PassCalculator
from libs.astronomy.orbital.tle import TLEParser
from libs.astronomy.planner.explanations import ExplanationBuilder
from libs.astronomy.planner.rules import MODE_PRIORITY
from libs.astronomy.visibility.ephemeris import EphemerisCalculator
from libs.astronomy.visibility.scoring import VisibilityScorer
from libs.astronomy.visibility.windows import VisibilityWindowCalculator

logger = logging.getLogger(__name__)


class NightScheduler:
    def __init__(self) -> None:
        self.ephemeris = EphemerisCalculator()
        self.scorer = VisibilityScorer(self.ephemeris)
        self.window_calculator = VisibilityWindowCalculator(ephemeris=self.ephemeris)
        self.explanations = ExplanationBuilder()

    def generate_plan(self, planner_request: PlannerRequest) -> PlannerResponse:
        observer = ObserverLocation(**planner_request.observer.model_dump())
        constraints = ObservingConstraints(
            min_alt_deg=planner_request.constraints.min_alt_deg,
            max_airmass=planner_request.constraints.max_airmass,
            moon_sep_min_deg=planner_request.constraints.moon_sep_min_deg,
            horizon_mask=HorizonMask(azimuth_to_min_altitude=planner_request.constraints.local_horizon_mask),
        )
        sun_alt, _ = self.ephemeris.get_sun_altaz(observer, planner_request.night_window.start_utc)
        moon_alt, _, moon_illumination = self.ephemeris.get_moon_altaz_and_illumination(observer, planner_request.night_window.start_utc)
        rejected: list[str] = []
        items: list[ContractPlanItem] = []

        planet_targets = {target.id: target for target in PlanetLoader().load()}
        orbital_parser = TLEParser()
        sample_tle_path = Path(__file__).resolve().parents[1] / 'catalogs' / 'datasets' / 'sample_tle.txt'
        orbital_records = {record.name: record for record in orbital_parser.parse_file(sample_tle_path)} if sample_tle_path.exists() else {}

        for ref in planner_request.targets:
            target = self._resolve_target(ref, planet_targets)
            if ref.kind == 'satellite' and ref.tle_name in orbital_records:
                record = orbital_records[ref.tle_name]
                passes = PassCalculator().compute_passes(record, observer, planner_request.night_window.start_utc, planner_request.night_window.end_utc, planner_request.constraints.min_alt_deg)
                if not passes:
                    rejected.append(ref.id)
                    continue
                best_pass = max(passes, key=lambda item: item.peak_alt_deg)
                items.append(
                    ContractPlanItem(
                        target_id=ref.id,
                        recommended_start_utc=best_pass.pass_start_utc,
                        recommended_end_utc=best_pass.pass_end_utc,
                        score_total=min(1.0, best_pass.peak_alt_deg / 90.0 * MODE_PRIORITY.get('orbital', 1.0)),
                        score_factors=[ScoreFactor(name='peak_altitude', value=best_pass.peak_alt_deg, weight=1.0, explanation='Orbital pass ranked by peak altitude.')],
                        mode='orbital',
                        risks=['WiFi latency not modeled.', 'Alt-az mount tracking depends on timely command delivery.'],
                        assumptions=['TLE accuracy may degrade rapidly for LEO satellites.'],
                    )
                )
                continue
            if target is None:
                rejected.append(ref.id)
                continue
            window = self.window_calculator.compute_window(target, observer, planner_request.night_window, constraints)
            if not window.is_visible or window.start_utc is None or window.end_utc is None or window.peak_alt_utc is None:
                rejected.append(ref.id)
                continue
            score = self.scorer.score_target(target, observer, window.peak_alt_utc, constraints, planner_request.equipment)
            mode = 'planetary' if target.kind in {TargetKind.PLANET, TargetKind.MOON} else 'eaa'
            adjusted_score = min(1.0, score.total_score * MODE_PRIORITY.get(mode, 1.0))
            items.append(
                ContractPlanItem(
                    target_id=target.id,
                    recommended_start_utc=window.start_utc,
                    recommended_end_utc=min(window.end_utc, window.start_utc + timedelta(hours=2)),
                    score_total=adjusted_score,
                    score_factors=[ScoreFactor(name=item.name, value=item.score, weight=item.weight, explanation=item.explanation) for item in score.contributions],
                    mode=mode,
                    risks=['Alt-az field rotation limits long sub-exposures.' if mode != 'planetary' else 'Seeing can dominate final planetary quality.'],
                    assumptions=['Heuristic ranking only.', 'Mount modeled as simple alt-az system.'],
                )
            )

        items.sort(key=lambda item: item.score_total, reverse=True)
        diagnostics = PlannerDiagnostics(
            sun_alt_deg=sun_alt,
            moon_alt_deg=moon_alt,
            moon_illumination=moon_illumination,
            rejected_targets=rejected,
            stale_data_flags=['Orbital planning uses sample offline TLEs when no cache is supplied.'],
        )
        return PlannerResponse(status='ok', plan_items=items, explanations=self.explanations.build(items), diagnostics=diagnostics)

    def _resolve_target(self, ref, planets: dict[str, Target]) -> Target | None:
        if ref.kind == 'planet':
            return planets.get(ref.id.lower())
        if ref.kind == 'moon':
            return planets.get(ref.id.lower())
        if ref.ra_deg is None or ref.dec_deg is None:
            return None
        kind = TargetKind(ref.kind) if ref.kind in {item.value for item in TargetKind} else TargetKind.CUSTOM
        return Target(id=ref.id, name=ref.id, kind=kind, ra_deg=ref.ra_deg, dec_deg=ref.dec_deg, tags=ref.tags)
