"""Filesystem-backed storage service."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from apps.backend.app.db.models import ManagedFile
from libs.config.settings import Settings
from libs.storage.models import IndexedFile, ReconciliationReport, StorageLayout


class StorageService:
    """Coordinates filesystem layout and DB file indexing."""

    def __init__(self, settings: Settings, session_factory: sessionmaker[Session]) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self.root_dir = Path(settings.data_dir)

    def ensure_runtime_directories(self) -> None:
        self.root_dir.mkdir(parents=True, exist_ok=True)
        (self.root_dir / "sessions").mkdir(parents=True, exist_ok=True)

    def session_layout(self, session_id: str) -> StorageLayout:
        session_root = self.root_dir / "sessions" / session_id
        return StorageLayout(
            session_root=session_root,
            captures_dir=session_root / "captures",
            previews_dir=session_root / "previews",
            metadata_dir=session_root / "metadata",
            logs_dir=session_root / "logs",
        )

    def ensure_session_layout(self, session_id: str) -> StorageLayout:
        layout = self.session_layout(session_id)
        for directory in (
            layout.session_root,
            layout.captures_dir,
            layout.previews_dir,
            layout.metadata_dir,
            layout.logs_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)
        return layout

    def write_bytes_atomic(self, relative_path: str, payload: bytes) -> Path:
        target = self.root_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(dir=target.parent, delete=False) as handle:
            handle.write(payload)
            temp_path = Path(handle.name)
        temp_path.replace(target)
        return target

    def write_json_atomic(self, relative_path: str, payload: dict[str, Any]) -> Path:
        return self.write_bytes_atomic(relative_path, json.dumps(payload, indent=2).encode("utf-8"))

    def index_file(
        self,
        *,
        session_id: str | None,
        kind: str,
        relative_path: str,
        metadata: dict[str, Any] | None = None,
    ) -> IndexedFile:
        target = self.root_dir / relative_path
        checksum = hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
        entry = ManagedFile(
            session_id=session_id,
            kind=kind,
            relative_path=relative_path,
            state="indexed" if target.exists() else "missing",
            size_bytes=target.stat().st_size if target.exists() else 0,
            checksum=checksum,
            metadata_json=metadata or {},
        )
        with self.session_factory() as db:
            db.add(entry)
            db.commit()
            db.refresh(entry)
            return IndexedFile(
                file_id=entry.id,
                relative_path=entry.relative_path,
                kind=entry.kind,
                state=entry.state,
                size_bytes=entry.size_bytes,
                metadata=entry.metadata_json,
            )

    def list_files(self, session_id: str | None = None) -> list[IndexedFile]:
        with self.session_factory() as db:
            stmt = select(ManagedFile).order_by(ManagedFile.created_at.desc())
            if session_id:
                stmt = stmt.where(ManagedFile.session_id == session_id)
            rows = db.scalars(stmt).all()
            return [
                IndexedFile(
                    file_id=row.id,
                    relative_path=row.relative_path,
                    kind=row.kind,
                    state=row.state,
                    size_bytes=row.size_bytes,
                    metadata=row.metadata_json,
                )
                for row in rows
            ]

    def persist_session_manifest(self, session_id: str, payload: dict[str, Any]) -> IndexedFile:
        layout = self.ensure_session_layout(session_id)
        relative_path = str((layout.metadata_dir / "session.json").relative_to(self.root_dir))
        self.write_json_atomic(relative_path, payload)
        return self.index_file(session_id=session_id, kind="session_manifest", relative_path=relative_path, metadata=payload)

    def reconcile_session(self, session_id: str) -> ReconciliationReport:
        layout = self.ensure_session_layout(session_id)
        indexed_paths = set()
        missing: list[str] = []
        recovered: list[str] = []
        with self.session_factory() as db:
            rows = db.scalars(select(ManagedFile).where(ManagedFile.session_id == session_id)).all()
            for row in rows:
                indexed_paths.add(row.relative_path)
                if not (self.root_dir / row.relative_path).exists():
                    row.state = "missing"
                    missing.append(row.relative_path)
            filesystem_paths: set[str] = set()
            for path in layout.session_root.rglob("*"):
                if path.is_file():
                    filesystem_paths.add(str(path.relative_to(self.root_dir)))
            orphaned = sorted(filesystem_paths - indexed_paths)
            for relative_path in orphaned:
                target = self.root_dir / relative_path
                db.add(
                    ManagedFile(
                        session_id=session_id,
                        kind="orphaned",
                        relative_path=relative_path,
                        state="orphaned",
                        size_bytes=target.stat().st_size,
                        metadata_json={"recovered": True},
                    )
                )
                recovered.append(relative_path)
            db.commit()
        return ReconciliationReport(
            missing_in_filesystem=missing,
            orphaned_in_filesystem=orphaned,
            recovered_to_index=recovered,
            checked_at=datetime.now(timezone.utc),
        )

