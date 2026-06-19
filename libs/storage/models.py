"""Storage-domain models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class StorageLayout:
    session_root: Path
    captures_dir: Path
    previews_dir: Path
    metadata_dir: Path
    logs_dir: Path


@dataclass(slots=True)
class ReconciliationReport:
    missing_in_filesystem: list[str]
    orphaned_in_filesystem: list[str]
    recovered_to_index: list[str]
    checked_at: datetime


@dataclass(slots=True)
class IndexedFile:
    file_id: str
    relative_path: str
    kind: str
    state: str
    size_bytes: int
    metadata: dict[str, Any]

