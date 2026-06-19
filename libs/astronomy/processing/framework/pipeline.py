"""Generic pipeline abstractions and runner."""

from __future__ import annotations

import logging
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from libs.astronomy.contracts.common import AstronomyError, JobKind, JobState, ResourceMetrics
from libs.astronomy.contracts.pipelines import JobRecord
from libs.astronomy.processing.framework.tracing import ExecutionTrace

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PipelineStepResult(BaseModel):
    step_name: str
    success: bool
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    runtime_ms: float = 0.0


class PipelineStep(ABC):
    name: str

    @abstractmethod
    def run(self, inputs: dict[str, Any], parameters: dict[str, Any], context: dict[str, Any]) -> PipelineStepResult:
        raise NotImplementedError


class Pipeline(BaseModel):
    id: str
    name: str
    kind: JobKind
    version: str
    steps: list[PipelineStep]
    description: str = ''

    model_config = {'arbitrary_types_allowed': True}


class PipelineRunner:
    def run(self, pipeline: Pipeline, inputs: dict[str, Any], parameters: dict[str, Any], trace_dir: str | Path) -> JobRecord:
        trace = ExecutionTrace(pipeline_id=pipeline.id)
        current_inputs = dict(inputs)
        started = utcnow()
        total_runtime = 0.0
        for step in pipeline.steps:
            start = time.perf_counter()
            result = step.run(current_inputs, parameters, {'pipeline_id': pipeline.id})
            result.runtime_ms = (time.perf_counter() - start) * 1000
            total_runtime += result.runtime_ms
            trace.steps.append(result.model_dump())
            if not result.success:
                trace_path = Path(trace_dir) / f'{pipeline.id}-trace.json'
                trace.save(trace_path)
                return JobRecord(
                    job_id=str(uuid.uuid4()),
                    pipeline_id=pipeline.id,
                    pipeline_version=pipeline.version,
                    kind=pipeline.kind,
                    state=JobState.FAILED,
                    session_id=parameters.get('session_id', 'unknown'),
                    inputs=inputs,
                    parameters=parameters,
                    metrics=ResourceMetrics(runtime_ms=total_runtime),
                    failure=AstronomyError(code='pipeline_step_failed', message=result.error or 'Pipeline step failed.'),
                    provenance={'trace_path': str(trace_path)},
                    created_at=started,
                    started_at=started,
                    completed_at=utcnow(),
                )
            current_inputs.update(result.output)
        trace_path = Path(trace_dir) / f'{pipeline.id}-trace.json'
        trace.save(trace_path)
        return JobRecord(
            job_id=str(uuid.uuid4()),
            pipeline_id=pipeline.id,
            pipeline_version=pipeline.version,
            kind=pipeline.kind,
            state=JobState.COMPLETED,
            session_id=parameters.get('session_id', 'unknown'),
            inputs=inputs,
            parameters=parameters,
            metrics=ResourceMetrics(runtime_ms=total_runtime),
            provenance={'trace_path': str(trace_path), 'final_output_keys': sorted(current_inputs)},
            created_at=started,
            started_at=started,
            completed_at=utcnow(),
        )
