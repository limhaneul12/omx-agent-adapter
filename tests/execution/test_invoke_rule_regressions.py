import subprocess

from execution.invoke import run_omx_command


def test_run_omx_command_normalizes_none_streams_without_or_fallback(monkeypatch) -> None:
    completed_process = subprocess.CompletedProcess(
        args=["omx", "status"],
        returncode=1,
        stdout=None,
        stderr=None,
    )

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: completed_process,
    )

    result = run_omx_command(["status"])

    assert result.stdout == ""
    assert result.stderr == ""
