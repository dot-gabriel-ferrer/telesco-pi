"""In-memory registry for named processing pipelines."""

from __future__ import annotations

from libs.astronomy.processing.framework.pipeline import Pipeline


class PipelineRegistry:
    def __init__(self) -> None:
        self._pipelines: dict[str, Pipeline] = {}

    def register(self, pipeline: Pipeline) -> None:
        self._pipelines[pipeline.id] = pipeline

    def get(self, pipeline_id: str) -> Pipeline | None:
        return self._pipelines.get(pipeline_id)

    def list(self) -> list[Pipeline]:
        return sorted(self._pipelines.values(), key=lambda pipeline: pipeline.id)
