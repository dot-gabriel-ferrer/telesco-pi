"""Simple on-disk JSON TLE cache with freshness tracking.

Any remote update path is intentionally optional and disabled by default.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from libs.astronomy.catalogs.models import TLEEntry
from libs.astronomy.orbital.tle import TLEParser

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TLEStore:
    def __init__(self, entries: list[TLEEntry] | None = None) -> None:
        self._entries: dict[str, TLEEntry] = {entry.name: entry for entry in (entries or [])}

    def load_from_file(self, path: str | Path) -> None:
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f'TLE source file not found: {file_path}')
        self.load_from_text(file_path.read_text(encoding='utf-8'), source=str(file_path))

    def load_from_text(self, text: str, source: str = 'inline') -> None:
        parser = TLEParser()
        for record in parser.parse_text(text, source=source):
            self._entries[record.name] = TLEEntry(
                name=record.name,
                line1=record.line1,
                line2=record.line2,
                source=record.source,
                fetched_at_utc=record.fetched_at_utc,
            )

    def get(self, name: str) -> TLEEntry | None:
        return self._entries.get(name)

    def get_all(self) -> list[TLEEntry]:
        return sorted(self._entries.values(), key=lambda entry: entry.name)

    def is_fresh(self, name: str, max_age_hours: float = 24) -> bool:
        entry = self.get(name)
        if entry is None:
            return False
        delta = utcnow() - entry.fetched_at_utc
        return delta.total_seconds() / 3600 <= max_age_hours

    def save(self, path: str | Path) -> Path:
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [entry.model_dump(mode='json') for entry in self.get_all()]
        file_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
        return file_path

    @classmethod
    def load(cls, path: str | Path) -> 'TLEStore':
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f'TLE cache file not found: {file_path}')
        payload = json.loads(file_path.read_text(encoding='utf-8'))
        return cls(entries=[TLEEntry.model_validate(entry) for entry in payload])

    def optional_remote_refresh(self) -> None:
        logger.info('OPTIONAL_REMOTE - disabled by default; no remote TLE fetch performed.')
