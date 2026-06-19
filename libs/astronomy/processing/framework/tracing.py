"""Execution trace persistence for processing pipelines."""

from __future__ import annotations

import json
from pathlib import Path
from pydantic import BaseModel, Field


class ExecutionTrace(BaseModel):
    pipeline_id: str
    steps: list[dict[str, object]] = Field(default_factory=list)

    def save(self, path: str | Path) -> Path:
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(self.model_dump_json(indent=2), encoding='utf-8')
        return file_path
