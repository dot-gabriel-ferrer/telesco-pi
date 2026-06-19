"""TLE parsing, validation, and age calculations."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TLERecord(BaseModel):
    name: str
    line1: str
    line2: str
    source: str = 'embedded'
    fetched_at_utc: datetime = Field(default_factory=utcnow)

    def validate(self) -> bool:
        return self.line1.startswith('1 ') and self.line2.startswith('2 ') and TLEParser.validate_checksum(self.line1) and TLEParser.validate_checksum(self.line2)

    @property
    def epoch_utc(self) -> datetime:
        year = int(self.line1[18:20])
        year += 2000 if year < 57 else 1900
        day_of_year = float(self.line1[20:32])
        return datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(days=day_of_year - 1)

    def age_hours(self, now_utc: datetime | None = None) -> float:
        now = now_utc or utcnow()
        return (now - self.epoch_utc).total_seconds() / 3600


class TLEParser:
    def parse_file(self, path: str | Path, source: str | None = None) -> list[TLERecord]:
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f'TLE file not found: {file_path}')
        return self.parse_text(file_path.read_text(encoding='utf-8'), source=source or str(file_path))

    def parse_text(self, text: str, source: str = 'inline') -> list[TLERecord]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if len(lines) % 3 != 0:
            raise ValueError('TLE text must contain name + two lines per record.')
        records: list[TLERecord] = []
        for index in range(0, len(lines), 3):
            record = TLERecord(name=lines[index], line1=lines[index + 1], line2=lines[index + 2], source=source)
            records.append(record)
        return records

    @staticmethod
    def validate_checksum(line: str) -> bool:
        if len(line) < 69:
            return False
        checksum = sum(int(char) for char in line[:68] if char.isdigit()) + sum(1 for char in line[:68] if char == '-')
        return checksum % 10 == int(line[68])
