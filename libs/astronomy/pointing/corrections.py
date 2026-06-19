"""Pointing correction wrappers for mount command preparation."""

from __future__ import annotations

from libs.astronomy.pointing.model import AltAzPointingModel


class PointingCorrector:
    def __init__(self, model: AltAzPointingModel | None = None) -> None:
        self.model = model or AltAzPointingModel()

    def apply(self, az_deg: float, alt_deg: float) -> tuple[float, float]:
        return self.model.correct(az_deg, alt_deg)
