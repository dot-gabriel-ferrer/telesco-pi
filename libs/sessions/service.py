"""Observation session service."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from apps.backend.app.db.models import ObservationSession
from libs.config.settings import Settings
from libs.sessions.models import SessionSummary
from libs.storage.service import StorageService


class SessionService:
    """Creates, resumes, closes, and restores sessions."""

    def __init__(
        self,
        settings: Settings,
        session_factory: sessionmaker[Session],
        storage_service: StorageService,
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self.storage_service = storage_service
        self._active_session_id: str | None = None

    def _to_summary(self, model: ObservationSession) -> SessionSummary:
        return SessionSummary(
            id=model.id,
            name=model.name,
            status=model.status,
            mode=model.mode,
            storage_path=model.storage_path,
            created_at=model.created_at,
            opened_at=model.opened_at,
            closed_at=model.closed_at,
            last_error=model.last_error,
            metadata=model.metadata_json,
        )

    def create_session(self, name: str, mode: str, metadata: dict | None = None) -> SessionSummary:
        with self.session_factory() as db:
            active = db.scalars(select(ObservationSession).where(ObservationSession.status == "active")).all()
            for session in active:
                session.status = "suspended"
            candidate = ObservationSession(
                name=name,
                status="active",
                mode=mode,
                storage_path=str(self.storage_service.session_layout("pending").session_root).replace("pending", ""),
                metadata_json=metadata or {},
            )
            db.add(candidate)
            db.flush()
            candidate.storage_path = str(self.storage_service.ensure_session_layout(candidate.id).session_root)
            db.commit()
            db.refresh(candidate)
            summary = self._to_summary(candidate)
            self._active_session_id = summary.id
            self.storage_service.persist_session_manifest(
                summary.id,
                {
                    "session": summary.model_dump(mode="json"),
                    "restorable": True,
                },
            )
            return summary

    def list_sessions(self) -> list[SessionSummary]:
        with self.session_factory() as db:
            rows = db.scalars(select(ObservationSession).order_by(ObservationSession.created_at.desc())).all()
            return [self._to_summary(row) for row in rows]

    def get_session(self, session_id: str) -> SessionSummary | None:
        with self.session_factory() as db:
            row = db.get(ObservationSession, session_id)
            return self._to_summary(row) if row else None

    def get_active_session(self) -> SessionSummary | None:
        if self._active_session_id:
            current = self.get_session(self._active_session_id)
            if current:
                return current
        with self.session_factory() as db:
            row = db.scalars(select(ObservationSession).where(ObservationSession.status == "active").limit(1)).first()
            if row:
                self._active_session_id = row.id
                return self._to_summary(row)
        return None

    def open_session(self, session_id: str) -> SessionSummary:
        with self.session_factory() as db:
            current_active = db.scalars(select(ObservationSession).where(ObservationSession.status == "active")).all()
            for row in current_active:
                row.status = "suspended"
            candidate = db.get(ObservationSession, session_id)
            if candidate is None:
                raise KeyError(session_id)
            candidate.status = "active"
            candidate.opened_at = datetime.now(timezone.utc)
            candidate.last_error = None
            db.commit()
            db.refresh(candidate)
            self._active_session_id = candidate.id
            return self._to_summary(candidate)

    def close_session(self, session_id: str) -> SessionSummary:
        with self.session_factory() as db:
            row = db.get(ObservationSession, session_id)
            if row is None:
                raise KeyError(session_id)
            row.status = "closed"
            row.closed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(row)
            if self._active_session_id == session_id:
                self._active_session_id = None
            return self._to_summary(row)

    def mark_corrupted(self, session_id: str, reason: str) -> SessionSummary:
        with self.session_factory() as db:
            row = db.get(ObservationSession, session_id)
            if row is None:
                raise KeyError(session_id)
            row.status = "corrupted"
            row.last_error = reason
            db.commit()
            db.refresh(row)
            if self._active_session_id == session_id:
                self._active_session_id = None
            return self._to_summary(row)

    def restore_last_session(self) -> SessionSummary | None:
        if not self.settings.auto_restore_last_session:
            return None
        with self.session_factory() as db:
            row = db.scalars(
                select(ObservationSession)
                .where(ObservationSession.status.in_(("active", "suspended")))
                .order_by(ObservationSession.updated_at.desc())
            ).first()
            if row is None:
                return None
            if not self.storage_service.session_layout(row.id).session_root.exists():
                row.status = "corrupted"
                row.last_error = "Session directory missing during restore."
                db.commit()
                return self._to_summary(row)
            row.status = "active"
            row.last_error = None
            db.commit()
            self._active_session_id = row.id
            return self._to_summary(row)
