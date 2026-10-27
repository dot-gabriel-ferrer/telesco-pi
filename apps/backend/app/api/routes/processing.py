"""Processing routes operate only on session-indexed originals."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from apps.backend.app.core.container import AppContainer
from apps.backend.app.core.dependencies import get_container
from libs.astronomy.contracts.common import QualityProfile
from libs.storage.models import IndexedFile

router = APIRouter(prefix="/processing", tags=["processing"])


class PlanetaryRequest(BaseModel):
    session_id: str
    file_ids: list[str] = Field(min_length=2, max_length=20)
    profile: QualityProfile = QualityProfile.BALANCED


class PlanetaryResponse(BaseModel):
    status: str
    file: IndexedFile
    array: IndexedFile
    preview: IndexedFile
    total_frames: int
    selected_frames: int
    notes: list[str]


@router.post("/planetary", response_model=PlanetaryResponse)
async def planetary(payload: PlanetaryRequest, container: AppContainer = Depends(get_container)) -> dict:
    result = await container.processing_service.planetary(payload.session_id, payload.file_ids, payload.profile)
    await container.event_bus.publish("processing.planetary.completed", "processing", {
        "session_id": payload.session_id, "total_frames": result["total_frames"],
        "selected_frames": result["selected_frames"],
    })
    return result
