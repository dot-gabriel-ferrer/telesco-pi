from __future__ import annotations

from pathlib import Path

from libs.astronomy.contracts.common import QualityProfile
from libs.astronomy.jobs.orchestration import JobOrchestrator
from libs.astronomy.jobs.models import JobState


def test_job_orchestration_and_persistence(tmp_path: Path) -> None:
    orchestrator = JobOrchestrator(tmp_path)
    job = orchestrator.submit('pipeline-1', {'input': 'x'}, {'kind': 'planner'}, 'session-1', QualityProfile.BALANCED)
    assert orchestrator.get_status(job.job_id).job_id == job.job_id
    cancelled = orchestrator.cancel(job.job_id)
    assert cancelled.state == JobState.CANCELLED
    jobs = orchestrator.list_jobs(session_id='session-1')
    assert jobs
