"""Session routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from apps.backend.app.api.schemas import FileListResponse, SessionCreateRequest, SessionListResponse, SessionOpenResponse
from apps.backend.app.core.container import AppContainer
from apps.backend.app.core.dependencies import get_container
from apps.backend.app.core.errors import AppError

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=SessionListResponse)
async def list_sessions(container: AppContainer = Depends(get_container)) -> SessionListResponse:
    return SessionListResponse(items=container.session_service.list_sessions())


@router.post("", response_model=SessionOpenResponse, status_code=201)
async def create_session(payload: SessionCreateRequest, container: AppContainer = Depends(get_container)) -> SessionOpenResponse:
    session = container.session_service.create_session(payload.name, payload.mode, payload.metadata)
    await container.event_bus.publish("session.created", "sessions", {"session_id": session.id, "mode": payload.mode})
    return SessionOpenResponse(session=session)


@router.get("/active", response_model=SessionOpenResponse)
async def active_session(container: AppContainer = Depends(get_container)) -> SessionOpenResponse:
    session = container.session_service.get_active_session()
    if session is None:
        raise AppError("session_not_found", "There is no active session.", status_code=404)
    return SessionOpenResponse(session=session)


@router.post("/{session_id}/open", response_model=SessionOpenResponse)
async def open_session(session_id: str, container: AppContainer = Depends(get_container)) -> SessionOpenResponse:
    try:
        session = container.session_service.open_session(session_id)
    except KeyError as exc:
        raise AppError("session_not_found", "Session not found.", status_code=404) from exc
    await container.event_bus.publish("session.opened", "sessions", {"session_id": session.id})
    return SessionOpenResponse(session=session)


@router.post("/{session_id}/close", response_model=SessionOpenResponse)
async def close_session(session_id: str, container: AppContainer = Depends(get_container)) -> SessionOpenResponse:
    try:
        session = container.session_service.close_session(session_id)
    except KeyError as exc:
        raise AppError("session_not_found", "Session not found.", status_code=404) from exc
    await container.event_bus.publish("session.closed", "sessions", {"session_id": session.id})
    return SessionOpenResponse(session=session)


@router.get("/{session_id}/files", response_model=FileListResponse)
async def session_files(session_id: str, container: AppContainer = Depends(get_container)) -> FileListResponse:
    return FileListResponse(items=container.storage_service.list_files(session_id))


@router.post("/{session_id}/reconcile", response_model=dict)
async def reconcile_session(session_id: str, container: AppContainer = Depends(get_container)) -> dict:
    report = container.storage_service.reconcile_session(session_id)
    await container.event_bus.publish("session.reconciled", "sessions", {"session_id": session_id})
    return {
        "session_id": session_id,
        "missing_in_filesystem": report.missing_in_filesystem,
        "orphaned_in_filesystem": report.orphaned_in_filesystem,
        "recovered_to_index": report.recovered_to_index,
        "checked_at": report.checked_at,
    }

