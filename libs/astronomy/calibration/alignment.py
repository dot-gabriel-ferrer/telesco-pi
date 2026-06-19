"""Calibration flow for simple initial alt-az alignment.

# STATUS: Pending validation with real hardware
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

from libs.astronomy.calibration.confidence import ConfidenceEstimator
from libs.astronomy.contracts.calibration import CalibrationResponse
from libs.astronomy.domain.observer import ObserverLocation
from libs.astronomy.domain.targets import Target
from libs.astronomy.pointing.model import AltAzPointingModel
from libs.astronomy.solving.astrometry_net import LocalAstrometryNetSolver

logger = logging.getLogger(__name__)


@dataclass
class CalibrationSession:
    observer: ObserverLocation
    target: Target
    mount_az_alt_guess: tuple[float, float]
    star_pairs: list[tuple[tuple[float, float], tuple[float, float]]] = field(default_factory=list)
    model: AltAzPointingModel = field(default_factory=AltAzPointingModel)


class CalibrationFlow:
    def __init__(self) -> None:
        self.confidence_estimator = ConfidenceEstimator()
        self.solver = LocalAstrometryNetSolver()

    def start_calibration(self, observer: ObserverLocation, target: Target, mount_az_alt_guess: tuple[float, float]) -> CalibrationSession:
        return CalibrationSession(observer=observer, target=target, mount_az_alt_guess=mount_az_alt_guess)

    def record_star_sync(self, session: CalibrationSession, measured_az_alt: tuple[float, float], expected_az_alt: tuple[float, float]) -> CalibrationResponse:
        session.star_pairs.append((measured_az_alt, expected_az_alt))
        residuals = session.model.fit(session.star_pairs)
        residual_mean = sum(residuals) / len(residuals)
        confidence = self.confidence_estimator.estimate(residual_mean, len(session.star_pairs))
        return CalibrationResponse(
            status='ok',
            confidence=confidence,
            offset_az_deg=session.model.az_offset,
            offset_alt_deg=session.model.alt_offset,
            notes=['Simple offset model updated.', 'Full n-term mount modeling is out of scope for this engine.'],
        )

    def solve_and_sync(self, image_path: str, observer: ObserverLocation, time_utc: datetime) -> CalibrationResponse:
        response = self.solver.solve(image_path=image_path, hint=None, timeout_s=60, profile='balanced')
        if response.status != 'ok':
            return CalibrationResponse(status='failed', confidence=0.0, notes=[response.diagnostics.reason_if_failed or 'Plate solve failed.'])
        return CalibrationResponse(status='ok', confidence=response.confidence_score, notes=['Plate-solve sync completed.', 'Hardware validation still pending.'])
