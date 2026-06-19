from __future__ import annotations

from libs.astronomy.pointing.model import AltAzPointingModel


def test_pointing_model_fit_and_correct() -> None:
    model = AltAzPointingModel()
    residuals = model.fit([
        ((100.0, 40.0), (101.0, 41.0)),
        ((200.0, 50.0), (201.0, 51.0)),
    ])
    corrected = model.correct(100.0, 40.0)
    assert residuals
    assert round(corrected[0], 1) == 101.0
