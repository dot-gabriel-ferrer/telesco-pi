"""Recommendation builder for orbital tracking strategies."""

from __future__ import annotations

from libs.astronomy.contracts.orbital import OrbitalPass


class OrbitalRecommendations:
    def for_pass(self, orbital_pass: OrbitalPass) -> list[str]:
        notes = ['Timing accuracy is critical.', 'WiFi latency is not modeled in this recommendation set.']
        if orbital_pass.peak_alt_deg < 20:
            notes.append('Low peak altitude reduces pass quality.')
        return notes
