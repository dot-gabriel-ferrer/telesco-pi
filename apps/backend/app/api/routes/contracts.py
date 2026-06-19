"""Stub routes for parallel integration work."""

from __future__ import annotations

from fastapi import APIRouter

from apps.backend.app.api.schemas import OrbitalRequest, OrbitalResponse, PlannerRequest, PlannerResponse

router = APIRouter(prefix="/contracts", tags=["contracts"])


@router.post("/planner", response_model=PlannerResponse)
async def planner_contract(payload: PlannerRequest) -> PlannerResponse:
    return PlannerResponse(
        status="stub",
        message="Planner contract reserved for astronomy-core integration.",
        items=[{"target": payload.target, "session_id": payload.session_id, "status": "pending_backend_integration"}],
    )


@router.post("/orbital", response_model=OrbitalResponse)
async def orbital_contract(payload: OrbitalRequest) -> OrbitalResponse:
    return OrbitalResponse(
        status="stub",
        message="Orbital contract reserved for astronomy-core integration.",
        passes=[{"object_id": payload.object_id, "status": "pending_backend_integration"}],
    )

