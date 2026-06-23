"""Astronomy engine integration routes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.backend.app.api.schemas import (
    OrbitalRequest,
    OrbitalResponse,
    PlannerRequest,
    PlannerResponse,
)
from apps.backend.app.core.container import AppContainer
from apps.backend.app.core.dependencies import get_container

router = APIRouter(prefix="/astronomy", tags=["astronomy"])


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------


@router.get("/catalog/search")
async def catalog_search(
    q: str = Query("", description="Search query (name or ID)"),
    kinds: str | None = Query(None, description="Comma-separated kinds: messier,star,planet,satellite"),
    max_results: int = Query(20, ge=1, le=100),
    container: AppContainer = Depends(get_container),
) -> dict[str, Any]:
    kind_list = [k.strip() for k in kinds.split(",")] if kinds else None
    results = container.astronomy_service.search_catalog(query=q, kinds=kind_list, max_results=max_results)
    return {"items": [r.model_dump() for r in results], "total": len(results)}


# ---------------------------------------------------------------------------
# Visibility
# ---------------------------------------------------------------------------


@router.post("/visibility")
async def check_visibility(
    payload: dict[str, Any],
    container: AppContainer = Depends(get_container),
) -> dict[str, Any]:
    target_id = payload.get("target_id", "")
    observer = payload.get("observer", {"lat_deg": 40.0, "lon_deg": -3.7, "elevation_m": 650.0})
    now = datetime.now(timezone.utc)
    night_window = payload.get("night_window", {"start_utc": now.isoformat(), "end_utc": (now + timedelta(hours=8)).isoformat()})
    constraints = payload.get("constraints")
    window = container.astronomy_service.compute_visibility(target_id, observer, night_window, constraints)
    if window is None:
        raise HTTPException(status_code=404, detail=f"Target '{target_id}' not found in catalog.")
    return window.model_dump()


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------


@router.post("/plan")
async def generate_plan(
    payload: dict[str, Any],
    container: AppContainer = Depends(get_container),
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    observer = payload.get("observer", {"lat_deg": 40.0, "lon_deg": -3.7, "elevation_m": 650.0})
    night_window = payload.get("night_window", {"start_utc": now.isoformat(), "end_utc": (now + timedelta(hours=8)).isoformat()})
    target_ids: list[str] = payload.get("targets", [])
    mode: str = payload.get("mode", "mixed")
    constraints = payload.get("constraints")
    request = container.astronomy_service.build_planner_request(
        target_ids=target_ids,
        observer=observer,
        night_window=night_window,
        mode=mode,
        constraints=constraints,
    )
    response = container.astronomy_service.generate_plan(request)
    return response.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Orbital
# ---------------------------------------------------------------------------


@router.get("/orbital/objects")
async def list_tle_objects(
    container: AppContainer = Depends(get_container),
) -> dict[str, Any]:
    records = container.astronomy_service.list_tle_objects()
    return {"items": [r.model_dump(mode="json") for r in records], "total": len(records)}


@router.post("/orbital/passes")
async def compute_orbital_passes(
    payload: dict[str, Any],
    container: AppContainer = Depends(get_container),
) -> dict[str, Any]:
    tle_name: str = payload.get("tle_name", "")
    observer = payload.get("observer", {"lat_deg": 40.0, "lon_deg": -3.7, "elevation_m": 650.0})
    now = datetime.now(timezone.utc)
    start_utc_raw = payload.get("start_utc", now.isoformat())
    end_utc_raw = payload.get("end_utc", (now + timedelta(hours=12)).isoformat())
    start_utc = datetime.fromisoformat(start_utc_raw) if isinstance(start_utc_raw, str) else start_utc_raw
    end_utc = datetime.fromisoformat(end_utc_raw) if isinstance(end_utc_raw, str) else end_utc_raw
    min_alt_deg: float = payload.get("min_alt_deg", 10.0)
    passes = container.astronomy_service.compute_passes(tle_name, observer, start_utc, end_utc, min_alt_deg)
    return {"tle_name": tle_name, "passes": [p.model_dump(mode="json") for p in passes], "total": len(passes)}


# ---------------------------------------------------------------------------
# Legacy stub aliases (kept for backward compat with older frontend calls)
# ---------------------------------------------------------------------------


@router.post("/contracts/planner", response_model=PlannerResponse, include_in_schema=False)
async def planner_contract_compat(payload: PlannerRequest) -> PlannerResponse:
    return PlannerResponse(
        status="stub",
        message="Use /api/v1/astronomy/plan instead.",
        items=[{"target": getattr(payload, "target", ""), "status": "redirect"}],
    )


@router.post("/contracts/orbital", response_model=OrbitalResponse, include_in_schema=False)
async def orbital_contract_compat(payload: OrbitalRequest) -> OrbitalResponse:
    return OrbitalResponse(
        status="stub",
        message="Use /api/v1/astronomy/orbital/passes instead.",
        passes=[{"object_id": payload.object_id, "status": "redirect"}],
    )
