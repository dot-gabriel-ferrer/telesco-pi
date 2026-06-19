"""Simple alt-az pointing model.

This is a three-parameter offset/scale model, not a full n-term mount model.
"""

from __future__ import annotations

import logging
from statistics import mean

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AltAzPointingModel(BaseModel):
    az_offset: float = 0.0
    alt_offset: float = 0.0
    scale_error: float = 0.0
    _confidence: float = 0.0

    def fit(self, star_pairs: list[tuple[tuple[float, float], tuple[float, float]]]) -> list[float]:
        if not star_pairs:
            raise ValueError('At least one star pair is required to fit the pointing model.')
        az_deltas = [expected[0] - measured[0] for measured, expected in star_pairs]
        alt_deltas = [expected[1] - measured[1] for measured, expected in star_pairs]
        self.az_offset = float(mean(az_deltas))
        self.alt_offset = float(mean(alt_deltas))
        mean_expected_alt = mean(expected[1] for _, expected in star_pairs)
        mean_measured_alt = mean(measured[1] for measured, _ in star_pairs)
        self.scale_error = 0.0 if mean_measured_alt == 0 else float((mean_expected_alt / mean_measured_alt) - 1.0)
        residuals: list[float] = []
        for measured, expected in star_pairs:
            corrected = self.correct(*measured)
            residuals.append(((corrected[0] - expected[0]) ** 2 + (corrected[1] - expected[1]) ** 2) ** 0.5)
        mean_residual = mean(residuals)
        self._confidence = float(max(0.0, min(1.0, 1.0 / (1.0 + mean_residual))))
        return residuals

    def correct(self, raw_az: float, raw_alt: float) -> tuple[float, float]:
        corrected_az = (raw_az + self.az_offset) % 360.0
        corrected_alt = (raw_alt + self.alt_offset) * (1.0 + self.scale_error)
        return corrected_az, corrected_alt

    def to_dict(self) -> dict[str, float]:
        return {'az_offset': self.az_offset, 'alt_offset': self.alt_offset, 'scale_error': self.scale_error, 'confidence': self._confidence}

    @classmethod
    def from_dict(cls, payload: dict[str, float]) -> 'AltAzPointingModel':
        model = cls(az_offset=payload.get('az_offset', 0.0), alt_offset=payload.get('alt_offset', 0.0), scale_error=payload.get('scale_error', 0.0))
        model._confidence = float(payload.get('confidence', 0.0))
        return model

    @property
    def confidence(self) -> float:
        return self._confidence
