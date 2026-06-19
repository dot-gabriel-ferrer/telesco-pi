"""Incremental live-stacking engine with bounded memory.

Limitations:
- Alt-az field rotation is not fully corrected.
- Alignment assumes small translational jitter.
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

import numpy as np
from scipy import stats
from skimage import exposure, registration, transform

from libs.astronomy.contracts.livestack import LiveStackState, RejectionReason, StackConfig
from libs.astronomy.processing.quality.metrics import FrameQualityMetrics

logger = logging.getLogger(__name__)


class LiveStackEngine:
    def __init__(self, config: StackConfig | None = None, persistence_path: str | None = None) -> None:
        self.config = config or StackConfig()
        self.metrics = FrameQualityMetrics()
        self.stack_id = str(uuid.uuid4())
        self.reference_frame: np.ndarray | None = None
        self.reference_frame_id: str | None = None
        self.frames: list[tuple[str, np.ndarray, float]] = []
        self.rejected: list[str] = []
        self.rejection_reasons: list[RejectionReason] = []
        self.persistence_path = persistence_path

    def add_frame(self, frame_array: np.ndarray, metadata: dict[str, object]) -> LiveStackState:
        if self.config.source_retention_policy != 'keep_best_n' and len(self.frames) >= self.config.max_frames_in_memory:
            raise MemoryError('Live stack memory budget exceeded.')
        frame_id = str(metadata.get('frame_id', f'frame-{len(self.frames)+1}'))
        if quality.score < 0.05:
            self.rejected.append(frame_id)
            self.rejection_reasons.append(RejectionReason(frame_id=frame_id, reason='quality_below_threshold', metric_value=quality.score))
            return self._build_state()
        if self.reference_frame is None:
            self.reference_frame = frame_array.astype(np.float32)
            self.reference_frame_id = frame_id
            aligned = self.reference_frame
        else:
            shift, error, _ = registration.phase_cross_correlation(self.reference_frame, frame_array.astype(np.float32), upsample_factor=10)
            aligned = transform.warp(frame_array.astype(np.float32), transform.AffineTransform(translation=(-shift[1], -shift[0])), preserve_range=True)
        self.frames.append((frame_id, aligned.astype(np.float32), quality.score))
        if self.config.source_retention_policy == 'keep_best_n' and len(self.frames) > self.config.max_frames_in_memory:
            self.frames.sort(key=lambda item: item[2], reverse=True)
            self.frames = self.frames[: self.config.max_frames_in_memory]
        state = self._build_state()
        if self.persistence_path:
            self.save(self.persistence_path)
        return state

    def _stack_array(self) -> np.ndarray | None:
        if not self.frames:
            return None
        stack = np.stack([item[1] for item in self.frames], axis=0)
        if self.config.accumulation_method == 'median':
            return np.median(stack, axis=0)
        if self.config.accumulation_method == 'kappa_sigma':
            mean = np.mean(stack, axis=0)
            std = np.std(stack, axis=0)
            lower = mean - self.config.kappa * std
            upper = mean + self.config.kappa * std
            masked = np.where((stack >= lower) & (stack <= upper), stack, np.nan)
            return np.nanmean(masked, axis=0)
        return np.mean(stack, axis=0)

    def preview_array(self) -> np.ndarray | None:
        stacked = self._stack_array()
        if stacked is None:
            return None
        norm = stacked / max(float(np.max(stacked)), 1.0)
        if self.config.stretch_method == 'asinh':
            return np.arcsinh(norm * 10) / np.arcsinh(10)
        return norm

    def save(self, persistence_path: str | Path) -> Path:
        base = Path(persistence_path)
        base.mkdir(parents=True, exist_ok=True)
        stack = self._stack_array()
        if stack is not None:
            np.save(base / 'stack.npy', stack)
        manifest = self._build_state().model_dump(mode='json')
        (base / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        return base

    @classmethod
    def resume(cls, persistence_path: str | Path) -> 'LiveStackEngine':
        base = Path(persistence_path)
        manifest = json.loads((base / 'manifest.json').read_text(encoding='utf-8'))
        engine = cls(config=StackConfig.model_validate(manifest['config']), persistence_path=str(base))
        engine.stack_id = manifest['stack_id']
        engine.reference_frame_id = manifest['reference_frame_id']
        return engine

    def _build_state(self) -> LiveStackState:
        preview_path = None
        if self.persistence_path and self._stack_array() is not None:
            preview_path = str(Path(self.persistence_path) / 'stack.npy')
        return LiveStackState(
            stack_id=self.stack_id,
            state='running',
            reference_frame_id=self.reference_frame_id,
            accepted_frames=[item[0] for item in self.frames],
            rejected_frames=list(self.rejected),
            rejection_reasons=list(self.rejection_reasons),
            alignment_quality_mean=float(np.mean([item[2] for item in self.frames])) if self.frames else 0.0,
            preview_artifact_path=preview_path,
            config=self.config,
            session_persistence_path=self.persistence_path,
            limitations=['Alt-az field rotation is not fully corrected.', 'Alignment is translation-only.'],
        )
