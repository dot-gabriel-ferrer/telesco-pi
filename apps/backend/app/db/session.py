"""Database session helpers."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from apps.backend.app.db.base import Base
from libs.config.settings import Settings


def create_database_engine(settings: Settings) -> Engine:
    connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    return create_engine(settings.database_url, connect_args=connect_args, future=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, autoflush=False, autocommit=False)


def initialize_database(engine: Engine, settings: Settings) -> None:
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine)

