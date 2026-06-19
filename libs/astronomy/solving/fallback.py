"""Remote fallback stub.

This module intentionally does not contact remote services by default.
"""

from __future__ import annotations

from libs.astronomy.contracts.solving import SolveDiagnostics, SolveResponse


class RemoteSolveFallback:
    def solve(self, *args, **kwargs) -> SolveResponse:
        return SolveResponse(
            status='failed',
            diagnostics=SolveDiagnostics(reason_if_failed='Remote fallback is disabled by default.'),
        )
