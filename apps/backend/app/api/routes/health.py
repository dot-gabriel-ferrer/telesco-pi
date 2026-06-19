"""Health routes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from apps.backend.app.api.schemas import HealthResponse
from apps.backend.app.core.dependencies import get_container
from apps.backend.app.core.container import AppContainer

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    return HealthResponse(status="ok", timestamp=datetime.now(timezone.utc), details={"liveness": "alive"})


@router.get("/ready", response_model=HealthResponse)
async def readiness(container: AppContainer = Depends(get_container)) -> HealthResponse:
    return HealthResponse(
        status="ok" if container.readiness() else "degraded",
        timestamp=datetime.now(timezone.utc),
        details={"readiness": container.readiness()},
    )

