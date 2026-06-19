"""Planetary frame-selection, alignment, stacking, and enhancement pipeline."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from scipy import ndimage
from skimage import exposure, filters, registration, transform

from libs.astronomy.contracts.common import QualityProfile
from libs.astronomy.processing.quality.metrics import FrameQualityMetrics

logger = logging.getLogger(__name__)


@dataclass
class PlanetaryJobResult:
    selected_frames: int
    total_frames: int
    stacked: np.ndarray
    artifacts: dict[str, str]
    notes: list[str]


class PlanetaryPipeline:
    MEMORY_BUDGETS = {QualityProfile.LOW: 20, QualityProfile.BALANCED: 50, QualityProfile.HIGH: 150}

    def __init__(self, profile: QualityProfile = QualityProfile.BALANCED) -> None:
        self.profile = profile
        self.metrics = FrameQualityMetrics()

    def process(self, frames: list[np.ndarray], output_dir: str | Path) -> PlanetaryJobResult:
        if not frames:
            raise ValueError('Planetary pipeline requires at least one frame.')
        max_frames = self.MEMORY_BUDGETS[self.profile]
        if len(frames) > max_frames:
            raise MemoryError(f'Frame set exceeds {self.profile.value} memory budget ({max_frames} frames).')
        scored = sorted(((self.metrics.score_frame(frame).score, frame) for frame in frames), key=lambda item: item[0], reverse=True)
        keep_fraction = {QualityProfile.LOW: 0.4, QualityProfile.BALANCED: 0.5, QualityProfile.HIGH: 0.7}[self.profile]
        selected = [frame for _, frame in scored[: max(1, int(len(scored) * keep_fraction))]]
        reference = selected[0].astype(np.float32)
        aligned: list[np.ndarray] = [reference]
        for frame in selected[1:]:
            shift, _, _ = registration.phase_cross_correlation(reference, frame.astype(np.float32), upsample_factor=10)
            aligned.append(ndimage.shift(frame.astype(np.float32), shift=shift, order=1, mode='nearest'))
        stacked = np.mean(np.stack(aligned, axis=0), axis=0)
        if self.profile == QualityProfile.LOW:
            sharpened = self._unsharp_mask(stacked, amount=1.0)
        else:
            sharpened = self._wavelet_like_sharpen(stacked)
        final = self._clahe(sharpened)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        artifact_path = output_path / f'planetary-{self.profile.value}.npy'
        np.save(artifact_path, final)
        return PlanetaryJobResult(
            selected_frames=len(selected),
            total_frames=len(frames),
            stacked=final,
            artifacts={'stacked_npy': str(artifact_path)},
            notes=['Alignment uses phase cross-correlation and is empirical.', 'Alt-az field rotation is not corrected frame-by-frame.'],
        )

    def _unsharp_mask(self, frame: np.ndarray, amount: float) -> np.ndarray:
        blurred = cv2.GaussianBlur(frame, (0, 0), 1.2)
        return np.clip(frame + amount * (frame - blurred), 0, np.max(frame))

    def _wavelet_like_sharpen(self, frame: np.ndarray) -> np.ndarray:
        low = filters.gaussian(frame, sigma=1.0)
        high = frame - low
        return np.clip(frame + 1.5 * high, 0, np.max(frame))

    def _clahe(self, frame: np.ndarray) -> np.ndarray:
        normalized = exposure.rescale_intensity(frame, out_range=(0, 1))
        return exposure.equalize_adapthist(normalized, clip_limit=0.03).astype(np.float32)
