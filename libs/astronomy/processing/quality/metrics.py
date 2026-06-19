"""Empirical frame-quality metrics.

# METRIC: Empirical proxy - not a physical measurement
"""

from __future__ import annotations

import logging

import cv2
import numpy as np

from libs.astronomy.contracts.planetary import FrameQuality

logger = logging.getLogger(__name__)


class FrameQualityMetrics:
    def compute_sharpness(self, frame_array: np.ndarray) -> float:
        # METRIC: Empirical proxy - not a physical measurement
        return float(cv2.Laplacian(frame_array.astype(np.float32), cv2.CV_32F).var())

    def compute_snr_estimate(self, frame_array: np.ndarray) -> float:
        # METRIC: Empirical proxy - not a physical measurement
        signal = float(np.mean(frame_array))
        noise = float(np.std(frame_array))
        return 0.0 if noise == 0 else signal / noise

    def compute_background(self, frame_array: np.ndarray) -> float:
        # METRIC: Empirical proxy - not a physical measurement
        return float(np.median(frame_array))

    def compute_centroid(self, frame_array: np.ndarray) -> tuple[float, float] | None:
        y, x = np.unravel_index(np.argmax(frame_array), frame_array.shape)
        if frame_array[y, x] <= 0:
            return None
        return float(x), float(y)

    def score_frame(self, frame_array: np.ndarray) -> FrameQuality:
        sharpness = self.compute_sharpness(frame_array)
        snr = self.compute_snr_estimate(frame_array)
        background = self.compute_background(frame_array)
        centroid = self.compute_centroid(frame_array)
        score = float(min(1.0, (sharpness / 1000.0) * 0.6 + min(snr / 20.0, 1.0) * 0.4))
        return FrameQuality(sharpness=sharpness, snr=snr, background=background, centroid=centroid, score=score, notes=['Empirical quality proxy only.'])
