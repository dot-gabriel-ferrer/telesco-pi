"""Thread-safe in-memory and on-disk job orchestrator."""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from libs.astronomy.contracts.common import JobKind, QualityProfile
from libs.astronomy.jobs.models import JobMetrics, JobRecord, JobState
from libs.astronomy.jobs.persistence import JobPersistence


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JobOrchestrator:
    def __init__(self, jobs_dir: str | Path) -> None:
        self.jobs_dir = Path(jobs_dir)
        self.persistence = JobPersistence()
        self.lock = threading.Lock()
        self.jobs: dict[str, JobRecord] = {job.job_id: job for job in self.persistence.list_all(self.jobs_dir)}

    def submit(self, pipeline_id: str, inputs: dict[str, object], parameters: dict[str, object], session_id: str, profile: QualityProfile) -> JobRecord:
        with self.lock:
            job = JobRecord(
                job_id=str(uuid.uuid4()),
                pipeline_id=pipeline_id,
                pipeline_version='1.0',
                kind=JobKind(parameters.get('kind', 'planner')),
                state=JobState.QUEUED,
                session_id=session_id,
                inputs=inputs,
                parameters={**parameters, 'profile': profile.value},
                metrics=JobMetrics(),
                created_at=utcnow(),
            )
            self.jobs[job.job_id] = job
            self.persistence.save(job, self.jobs_dir)
            return job

    def get_status(self, job_id: str) -> JobRecord:
        with self.lock:
            if job_id not in self.jobs:
                raise KeyError(f'Unknown job id: {job_id}')
            return self.jobs[job_id]

    def cancel(self, job_id: str) -> JobRecord:
        with self.lock:
            if job_id not in self.jobs:
                raise KeyError(f'Unknown job id: {job_id}')
            job = self.jobs[job_id]
            cancelled = job.model_copy(update={'state': JobState.CANCELLED, 'completed_at': utcnow()})
            self.jobs[job_id] = cancelled
            self.persistence.save(cancelled, self.jobs_dir)
            return cancelled

    def list_jobs(self, state_filter: JobState | None = None, session_id: str | None = None) -> list[JobRecord]:
        with self.lock:
            jobs = list(self.jobs.values())
        if state_filter is not None:
            jobs = [job for job in jobs if job.state == state_filter]
        if session_id is not None:
            jobs = [job for job in jobs if job.session_id == session_id]
        return sorted(jobs, key=lambda job: job.created_at)
