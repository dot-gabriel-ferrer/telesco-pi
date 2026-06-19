"""JSON persistence for astronomy job records."""

from __future__ import annotations

import json
from pathlib import Path

from libs.astronomy.jobs.models import JobRecord


class JobPersistence:
    def save(self, job_record: JobRecord, jobs_dir: str | Path) -> Path:
        base = Path(jobs_dir)
        base.mkdir(parents=True, exist_ok=True)
        path = base / f'{job_record.job_id}.json'
        path.write_text(job_record.model_dump_json(indent=2), encoding='utf-8')
        return path

    def load(self, job_id: str, jobs_dir: str | Path) -> JobRecord:
        path = Path(jobs_dir) / f'{job_id}.json'
        return JobRecord.model_validate_json(path.read_text(encoding='utf-8'))

    def list_all(self, jobs_dir: str | Path) -> list[JobRecord]:
        base = Path(jobs_dir)
        if not base.exists():
            return []
        return [JobRecord.model_validate_json(path.read_text(encoding='utf-8')) for path in sorted(base.glob('*.json'))]
