import subprocess

import pytest
from pydantic import ValidationError

from execution.invoke import run_omx_command
from schemas.invoke_schemas import OmxCommandResult


def test_omx_command_result_accepts_exit_code_stdout_and_stderr() -> None:
    result = OmxCommandResult.model_validate(
        {"exit_code": 0, "stdout": "ok", "stderr": ""}
    )

    assert result.exit_code == 0
    assert result.stdout == "ok"
    assert result.stderr == ""


def test_omx_command_result_rejects_unexpected_extra_fields() -> None:
    with pytest.raises(ValidationError):
        OmxCommandResult.model_validate(
            {
                "exit_code": 0,
                "stdout": "ok",
                "stderr": "",
                "unexpected": True,
            }
        )


def test_run_omx_command_returns_typed_command_result(monkeypatch) -> None:
    completed_process = subprocess.CompletedProcess(
        args=["omx", "status"],
        returncode=3,
        stdout="runtime down\n",
        stderr="failed\n",
    )

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: completed_process,
    )

    result = run_omx_command(["status"], cwd="/tmp/demo")

    assert result == OmxCommandResult(
        exit_code=3,
        stdout="runtime down\n",
        stderr="failed\n",
    )


def test_run_omx_command_passes_expected_subprocess_arguments(monkeypatch) -> None:
    seen_arguments: dict[str, object] = {}

    def fake_run(*args, **kwargs) -> subprocess.CompletedProcess[str]:
        seen_arguments["args"] = args
        seen_arguments["kwargs"] = kwargs
        return subprocess.CompletedProcess(
            args=["omx", "status"],
            returncode=0,
            stdout="ok\n",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    run_omx_command(["status"], cwd="/tmp/demo")

    assert seen_arguments["args"] == (["omx", "status"],)
    assert seen_arguments["kwargs"] == {
        "cwd": "/tmp/demo",
        "text": True,
        "capture_output": True,
        "check": False,
    }
