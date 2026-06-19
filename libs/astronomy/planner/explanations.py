"""Human-readable explanation builders for planner outputs."""

from __future__ import annotations

from libs.astronomy.contracts.planning import PlanItem


class ExplanationBuilder:
    def build(self, plan_items: list[PlanItem]) -> list[str]:
        explanations: list[str] = []
        for item in plan_items:
            explanations.append(
                f"{item.target_id}: {item.mode} window from {item.recommended_start_utc.isoformat()} to {item.recommended_end_utc.isoformat()} score={item.score_total:.2f}."
            )
        if not explanations:
            explanations.append('No targets met the requested planning constraints.')
        return explanations
