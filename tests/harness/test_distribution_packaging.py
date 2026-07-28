from __future__ import annotations

import subprocess
from pathlib import Path
from zipfile import ZipFile

REPOSITORY_ROOT = Path(__file__).parents[2]


def test_wheel_contains_the_ade_and_excludes_removed_runtime_surfaces(
    tmp_path: Path,
) -> None:
    completed = subprocess.run(
        ("uv", "build", "--wheel", "--out-dir", str(tmp_path)),
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    wheel_path = next(tmp_path.glob("*.whl"))
    with ZipFile(wheel_path) as wheel:
        members = set(wheel.namelist())

    assert "comx_harness/ade/tk_app.py" in members
    assert "comx_harness/ade/worker.py" in members
    assert "comx_harness/ade/agent_platform.py" in members
    assert "comx_harness/ade/agent_operations.py" in members
    assert "comx_harness/ade/agent_cli.py" in members
    assert "comx_harness/schemas/ade_agent_schemas.py" in members
    assert "comx_harness/application/harness_service.py" in members
    assert not any(member.startswith("comx_harness/tui/") for member in members)
    assert not any(member.startswith("omx_remote/") for member in members)
    assert "omx_agent_adapter_cli.py" not in members
