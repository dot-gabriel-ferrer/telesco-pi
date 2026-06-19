"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.backend.app.api.router import build_router
from apps.backend.app.core.container import AppContainer
from apps.backend.app.core.errors import register_exception_handlers
from apps.backend.app.middleware.request_context import RequestContextMiddleware
from libs.config.settings import Settings
from libs.diagnostics.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings()
    configure_logging(app_settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        container = AppContainer.build(app_settings)
        app.state.container = container
        await container.start()
        try:
            yield
        finally:
            await container.stop()

    app = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        lifespan=lifespan,
        openapi_url=f"{app_settings.api_v1_prefix}/openapi.json",
        docs_url=f"{app_settings.api_v1_prefix}/docs",
        redoc_url=f"{app_settings.api_v1_prefix}/redoc",
    )
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.include_router(build_router(), prefix=app_settings.api_v1_prefix)
    return app


app = create_app()
