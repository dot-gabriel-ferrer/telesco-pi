"""Confidence estimation for simple calibration sessions."""

from __future__ import annotations

from math import exp


class ConfidenceEstimator:
    def estimate(self, residual_deg: float, sync_points: int) -> float:
        return float(max(0.0, min(1.0, exp(-abs(residual_deg)) * min(1.0, sync_points / 3))))
