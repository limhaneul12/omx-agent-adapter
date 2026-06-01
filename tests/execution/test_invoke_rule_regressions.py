import subprocess

from omx_remote.execution.invoke import run_omx_command


def test_run_omx_command_normalizes_none_streams_without_or_fallback(
    monkeypatch,
) -> None:
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


def test_run_omx_command_maps_permission_error_to_126(monkeypatch) -> None:
    def _raise_permission_error(*args, **kwargs):
        raise PermissionError("denied")

    monkeypatch.setattr(subprocess, "run", _raise_permission_error)

    result = run_omx_command(["status"])

    assert result.exit_code == 126
    assert result.stdout == ""
    assert result.stderr == "denied"


def test_run_omx_command_maps_generic_oserror_to_1(monkeypatch) -> None:
    def _raise_oserror(*args, **kwargs):
        raise OSError("boom")

    monkeypatch.setattr(subprocess, "run", _raise_oserror)

    result = run_omx_command(["status"])

    assert result.exit_code == 1
    assert result.stdout == ""
    assert result.stderr == "boom"
