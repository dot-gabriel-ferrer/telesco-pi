from __future__ import annotations

from libs.astronomy.processing.quality.metrics import FrameQualityMetrics
from libs.astronomy.testdata.synthetic_frames.generators import SyntheticFrameGenerator


def test_quality_metrics_and_generators() -> None:
    generator = SyntheticFrameGenerator()
    frame = generator.generate_star_field(128, 128, n_stars=20, seed=1)
    metrics = FrameQualityMetrics()
    quality = metrics.score_frame(frame)
    assert quality.sharpness >= 0
    assert quality.centroid is not None
    frames = generator.generate_frame_sequence(5, seed=2)
    assert len(frames) == 5
