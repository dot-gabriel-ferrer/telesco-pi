"""Tracking-command generation for orbital passes.

Timing accuracy is critical and WiFi latency is not modeled.
"""

from __future__ import annotations

from libs.astronomy.contracts.common import QualityProfile
from libs.astronomy.contracts.orbital import OrbitalPass, TrackPoint


class TrackingCommandGenerator:
    RATES = {QualityProfile.LOW: 0.5, QualityProfile.BALANCED: 1.0, QualityProfile.HIGH: 2.0}
    MAX_SLEW_RATE_DEG_S = 4.0

    def generate_track_commands(self, orbital_pass: OrbitalPass, update_hz: float = 1.0) -> list[TrackPoint]:
        return list(orbital_pass.az_alt_track)

    def estimate_warnings(self, orbital_pass: OrbitalPass) -> list[str]:
        warnings = list(orbital_pass.tracking_warnings)
        points = orbital_pass.az_alt_track
        for first, second in zip(points, points[1:]):
            dt = max((second.utc - first.utc).total_seconds(), 1e-6)
            az_rate = abs(second.az_deg - first.az_deg) / dt
            alt_rate = abs(second.alt_deg - first.alt_deg) / dt
            if max(az_rate, alt_rate) > self.MAX_SLEW_RATE_DEG_S:
                warnings.append('estimated_slew_rate_exceeds_mount_capability')
                break
        return warnings
