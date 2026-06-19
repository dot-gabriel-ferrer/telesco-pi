"""ORM models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.backend.app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ObservationSession(Base):
    __tablename__ = "observation_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(32), index=True)
    mode: Mapped[str] = mapped_column(String(32), index=True)
    storage_path: Mapped[str] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    files: Mapped[list["ManagedFile"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class ManagedFile(Base):
    __tablename__ = "managed_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str | None] = mapped_column(ForeignKey("observation_sessions.id"), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    relative_path: Mapped[str] = mapped_column(String(255), unique=True)
    state: Mapped[str] = mapped_column(String(32), default="indexed", index=True)
    size_bytes: Mapped[int] = mapped_column(default=0)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped[ObservationSession | None] = relationship(back_populates="files")

