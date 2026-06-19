"""Confidence scoring for plate-solve results."""

from __future__ import annotations


class SolveConfidence:
    def evaluate(self, residual_arcsec: float | None, stars_used: int) -> float:
        if residual_arcsec is None:
            return 0.0
        return float(max(0.0, min(1.0, (stars_used / 50.0) * (1.0 / (1.0 + residual_arcsec)))))
