"""Image preprocessing for plate solving."""

from __future__ import annotations

import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class SolvePreprocessor:
    def prepare_for_solve(self, image_array: np.ndarray, profile: str) -> np.ndarray:
        if image_array.ndim not in {2, 3}:
            raise ValueError('Plate-solving preprocessing expects a 2D or 3D image array.')
        gray = image_array if image_array.ndim == 2 else cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
        normalized = cv2.normalize(gray, None, 0, 65535, cv2.NORM_MINMAX)
        max_size = {'low': 800, 'balanced': 1200, 'high': max(gray.shape)}.get(profile, 1200)
        h, w = normalized.shape[:2]
        longest = max(h, w)
        if longest > max_size:
            scale = max_size / longest
            normalized = cv2.resize(normalized, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        return normalized.astype(np.uint16)
