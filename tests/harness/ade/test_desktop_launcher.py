from __future__ import annotations

import os
from pathlib import Path

import pytest
from comx_harness.ade import desktop_launcher


def test_launcher_bridges_packages_into_a_tk_capable_interpreter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = tmp_path / "python3"
    candidate.touch()
    launched: dict[str, object] = {}

    monkeypatch.setattr(
        desktop_launcher,
        "_tk_interpreter",
        lambda current: candidate,
    )
    monkeypatch.setattr(
        desktop_launcher.os,
        "execve",
        lambda executable, argv, environment: launched.update(
            executable=executable,
            argv=argv,
            environment=environment,
        ),
    )

    desktop_launcher.launch_desktop_ade(tmp_path)

    assert launched["executable"] == candidate
    assert str(tmp_path.resolve()) == launched["argv"][-1]
    environment = launched["environment"]
    assert isinstance(environment, dict)
    assert environment["PYTHONPATH"]


def test_launcher_reports_missing_desktop_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        desktop_launcher,
        "_tk_interpreter",
        lambda current: None,
    )
    monkeypatch.setattr(desktop_launcher, "_current_tk_is_usable", lambda: False)

    with pytest.raises(RuntimeError, match="usable Tk support"):
        desktop_launcher.launch_desktop_ade(tmp_path)


def test_bridge_environment_preserves_existing_pythonpath(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYTHONPATH", "existing-path")

    environment = desktop_launcher._bridge_environment()

    assert environment["PYTHONPATH"].split(os.pathsep)[-1] == "existing-path"
