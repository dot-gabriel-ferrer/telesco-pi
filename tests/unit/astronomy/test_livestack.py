from __future__ import annotations

from pathlib import Path

from libs.astronomy.contracts.livestack import StackConfig
from libs.astronomy.processing.livestack.engine import LiveStackEngine
from libs.astronomy.testdata.synthetic_frames.generators import SyntheticFrameGenerator


def test_live_stack_engine(tmp_path: Path) -> None:
    generator = SyntheticFrameGenerator()
    frames = generator.generate_frame_sequence(4, seed=3)
    engine = LiveStackEngine(config=StackConfig(max_frames_in_memory=8), persistence_path=str(tmp_path))
    for index, frame in enumerate(frames):
        state = engine.add_frame(frame, {'frame_id': f'f{index}'})
    assert state.accepted_frames
    resumed = LiveStackEngine.resume(tmp_path)
    assert resumed.stack_id == engine.stack_id
