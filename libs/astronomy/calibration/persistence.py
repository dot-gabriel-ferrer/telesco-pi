"""JSON persistence for calibration reference data and pointing state."""

from __future__ import annotations

import json
from pathlib import Path

from libs.astronomy.calibration.reference_state import CalibrationReference
from libs.astronomy.pointing.model import AltAzPointingModel


class CalibrationPersistence:
    def save(self, path: str | Path, reference: CalibrationReference, model: AltAzPointingModel) -> Path:
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {'reference': reference.model_dump(mode='json'), 'model': model.to_dict()}
        file_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
        return file_path

    def load(self, path: str | Path) -> tuple[CalibrationReference, AltAzPointingModel]:
        file_path = Path(path)
        payload = json.loads(file_path.read_text(encoding='utf-8'))
        return CalibrationReference.model_validate(payload['reference']), AltAzPointingModel.from_dict(payload['model'])
