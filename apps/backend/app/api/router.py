"""API router."""

from fastapi import APIRouter

from apps.backend.app.api.routes import contracts, devices, health, sessions, system, ws


def build_router() -> APIRouter:
    router = APIRouter()
    router.include_router(health.router)
    router.include_router(system.router)
    router.include_router(sessions.router)
    router.include_router(devices.router)
    router.include_router(contracts.router)
    router.include_router(ws.router)
    return router

