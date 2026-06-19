"""System routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from apps.backend.app.api.schemas import SystemStatusResponse
from apps.backend.app.core.container import AppContainer
from apps.backend.app.core.dependencies import get_container
from apps.backend.app.services.system_service import SystemService

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status", response_model=SystemStatusResponse)
async def system_status(container: AppContainer = Depends(get_container)) -> SystemStatusResponse:
    return await SystemService(container).status()

