"""Synthetic frame generators for deterministic astronomy tests.

All frames are synthetic and not meant to model instrument physics exactly.
"""

from __future__ import annotations

import logging

import numpy as np
from scipy.ndimage import gaussian_filter, shift

logger = logging.getLogger(__name__)


class SyntheticFrameGenerator:
    def generate_star_field(self, width: int, height: int, n_stars: int = 50, noise_level: float = 5.0, seed: int | None = None) -> np.ndarray:
        rng = np.random.default_rng(seed)
        frame = np.zeros((height, width), dtype=np.float32)
        ys = rng.integers(5, height - 5, size=n_stars)
        xs = rng.integers(5, width - 5, size=n_stars)
        fluxes = rng.uniform(50, 255, size=n_stars)
        for x, y, flux in zip(xs, ys, fluxes):
            frame[y, x] += flux
        frame = gaussian_filter(frame, sigma=1.2)
        frame += rng.normal(0, noise_level, size=frame.shape).astype(np.float32)
        return np.clip(frame, 0, 255).astype(np.float32)

    def generate_planet_disk(self, width: int, height: int, disk_radius_px: int = 20, noise_level: float = 3.0, seed: int | None = None) -> np.ndarray:
        rng = np.random.default_rng(seed)
        yy, xx = np.mgrid[:height, :width]
        cx, cy = width / 2, height / 2
        disk = ((xx - cx) ** 2 + (yy - cy) ** 2) <= disk_radius_px**2
        frame = np.zeros((height, width), dtype=np.float32)
        frame[disk] = 180.0
        frame = gaussian_filter(frame, sigma=1.0)
        frame += rng.normal(0, noise_level, size=frame.shape).astype(np.float32)
        return np.clip(frame, 0, 255).astype(np.float32)

    def generate_frame_sequence(self, n_frames: int, kind: str = 'star', jitter_px: float = 1.5, noise_levels: tuple[float, float] = (2.0, 5.0), seed: int | None = None) -> list[np.ndarray]:
        rng = np.random.default_rng(seed)
        base = self.generate_star_field(128, 128, seed=seed) if kind == 'star' else self.generate_planet_disk(128, 128, seed=seed)
        frames: list[np.ndarray] = []
        for _ in range(n_frames):
            delta = rng.normal(0, jitter_px, size=2)
            noisy = shift(base, shift=delta, order=1, mode='nearest')
            noisy += rng.normal(0, rng.uniform(*noise_levels), size=base.shape)
            frames.append(np.clip(noisy, 0, 255).astype(np.float32))
        return frames
