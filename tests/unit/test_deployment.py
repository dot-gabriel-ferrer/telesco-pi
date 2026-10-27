from pathlib import Path
import shutil
import subprocess
import sys

import pytest


def test_systemd_definition(tmp_path):
    executable = shutil.which("systemd-analyze")
    if executable is None:
        pytest.skip("systemd-analyze is only available on systemd hosts")
    root = Path(__file__).resolve().parents[2]
    source = root / "infra/systemd/telesco-pi.service"
    # Validate the shipped unit without installing it or requiring /opt on CI.
    unit = source.read_text().replace("/opt/telesco-pi/.venv/bin/python", sys.executable)
    target = tmp_path / source.name
    target.write_text(unit)
    result = subprocess.run([executable, "verify", str(target)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
