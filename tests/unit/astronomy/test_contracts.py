from __future__ import annotations

from datetime import datetime, timezone

from libs.astronomy.contracts.common import DataSource, QualityProfile, RequestEnvelope
from libs.astronomy.contracts.livestack import LiveStackState, StackConfig
from libs.astronomy.contracts.orbital import OrbitalResponse
from libs.astronomy.contracts.planning import EquipmentSpec, ObserverSpec, PlannerRequest, TargetRef, TimeWindow
from libs.astronomy.contracts.solving import ImageMetadata, SolveRequest


def test_request_envelope_defaults() -> None:
    envelope = RequestEnvelope(request_id='req-1', session_id='sess-1')
    assert envelope.profile == QualityProfile.BALANCED
    assert envelope.source == DataSource.SIMULATOR


def test_planner_request_validation() -> None:
    request = PlannerRequest(
        request_id='p1',
        session_id='s1',
        observer=ObserverSpec(lat_deg=40, lon_deg=-3, elevation_m=600, timezone_name='UTC'),
        equipment=EquipmentSpec(focal_length_mm=650, aperture_mm=130, camera_pixel_size_um=2.9, camera_resolution=(1920, 1080)),
        night_window=TimeWindow(start_utc=datetime(2026, 1, 1, 20, tzinfo=timezone.utc), end_utc=datetime(2026, 1, 2, 2, tzinfo=timezone.utc)),
        targets=[TargetRef(id='M13', kind='messier', tags=['globular'], ra_deg=250.421, dec_deg=36.459)],
    )
    assert request.targets[0].id == 'M13'


def test_solve_request_validation() -> None:
    request = SolveRequest(
        request_id='solve-1',
        session_id='session-1',
        image_path='sample.fits',
        metadata=ImageMetadata(width=100, height=100, format='fits'),
    )
    assert request.metadata.width == 100


def test_livestack_state_validation() -> None:
    state = LiveStackState(stack_id='stack-1', state='running', config=StackConfig())
    assert state.config.accumulation_method == 'mean'


def test_orbital_response_defaults() -> None:
    response = OrbitalResponse(status='ok')
    assert response.passes == []
