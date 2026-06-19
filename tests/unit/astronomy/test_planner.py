from __future__ import annotations

import json
from pathlib import Path

from libs.astronomy.contracts.planning import EquipmentSpec, ObserverSpec, PlannerConstraints, PlannerRequest, TargetRef, TimeWindow
from libs.astronomy.planner.scheduler import NightScheduler

ROOT = Path(__file__).resolve().parents[3]


def test_planner_generates_plan() -> None:
    scenario = json.loads((ROOT / 'libs/astronomy/testdata/scenarios/sample_night.json').read_text(encoding='utf-8'))
    request = PlannerRequest(
        request_id='planner-1',
        session_id='session-1',
        observer=ObserverSpec(**scenario['observer']),
        equipment=EquipmentSpec(focal_length_mm=650, aperture_mm=130, camera_pixel_size_um=2.9, camera_resolution=(1920, 1080)),
        night_window=TimeWindow(**scenario['night_window']),
        targets=[TargetRef(**target) for target in scenario['targets']],
        constraints=PlannerConstraints(**scenario['constraints']),
        mode=scenario['mode'],
    )
    response = NightScheduler().generate_plan(request)
    assert response.status == 'ok'
    assert response.plan_items
