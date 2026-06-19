"""Image loading and saving helpers for astronomy workflows."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from astropy.io import fits


class ImageIO:
    def load_pgm(self, path: str | Path) -> np.ndarray:
        array = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if array is None:
            raise FileNotFoundError(f'PGM file could not be loaded: {path}')
        return array

    def load_fits(self, path: str | Path) -> tuple[np.ndarray, dict[str, object]]:
        with fits.open(path) as hdul:
            return np.array(hdul[0].data), dict(hdul[0].header)

    def load_png_tiff(self, path: str | Path) -> np.ndarray:
        array = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if array is None:
            raise FileNotFoundError(f'Image file could not be loaded: {path}')
        return array

    def save_fits(self, array: np.ndarray, path: str | Path, header_dict: dict[str, object] | None = None) -> Path:
        fits.PrimaryHDU(array, header=fits.Header(header_dict or {})).writeto(path, overwrite=True)
        return Path(path)

    def save_png(self, array: np.ndarray, path: str | Path, bit_depth: int = 8) -> Path:
        scaled = array.astype(np.uint16 if bit_depth == 16 else np.uint8)
        if not cv2.imwrite(str(path), scaled):
            raise OSError(f'PNG save failed: {path}')
        return Path(path)

    def save_tiff(self, array: np.ndarray, path: str | Path) -> Path:
        if not cv2.imwrite(str(path), array):
            raise OSError(f'TIFF save failed: {path}')
        return Path(path)

    def frame_to_bytes_pgm(self, array: np.ndarray) -> bytes:
        arr = np.clip(array, 0, 255).astype(np.uint8)
        header = f"P5\n{arr.shape[1]} {arr.shape[0]}\n255\n".encode('ascii')
        return header + arr.tobytes()
