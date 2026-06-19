"""WCS fit helpers for deriving approximate image-pointing offsets."""

from __future__ import annotations

import numpy as np


def estimate_linear_wcs(pixel_points: list[tuple[float, float]], sky_points_deg: list[tuple[float, float]]) -> dict[str, float]:
    if len(pixel_points) != len(sky_points_deg) or len(pixel_points) < 2:
        raise ValueError('At least two matched pixel/sky points are required.')
    x = np.array([point[0] for point in pixel_points], dtype=float)
    y = np.array([point[1] for point in pixel_points], dtype=float)
    ra = np.array([point[0] for point in sky_points_deg], dtype=float)
    dec = np.array([point[1] for point in sky_points_deg], dtype=float)
    return {
        'ra_slope': float(np.polyfit(x, ra, 1)[0]),
        'dec_slope': float(np.polyfit(y, dec, 1)[0]),
        'ra_intercept': float(np.polyfit(x, ra, 1)[1]),
        'dec_intercept': float(np.polyfit(y, dec, 1)[1]),
    }
