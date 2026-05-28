from omx_remote.runtime.ultragoal.ultragoal_status import read_ultragoal_status
from omx_remote.schemas.invoke.command_schemas import OmxCommandResult
from omx_remote.schemas.ultragoal.status_schemas import (
    UltragoalNativeState,
    UltragoalStatusResult,
)


def test_ultragoal_status_result_wraps_capability_and_status_results() -> None:
    result = UltragoalStatusResult(
        state=UltragoalNativeState.AVAILABLE,
        supported=True,
        capability_command=("ultragoal", "--help"),
        capability_result=OmxCommandResult(exit_code=0, stdout="help", stderr=""),
        status_command=("ultragoal", "status", "--json"),
        status_result=OmxCommandResult(
            exit_code=0,
            stdout='{"summary":{"complete":0}}',
            stderr="",
        ),
    )

    assert result.supported is True
    assert result.state == UltragoalNativeState.AVAILABLE
    assert result.status_result is not None


def test_read_ultragoal_status_reports_missing_omx_without_status_probe(
    monkeypatch,
) -> None:
    seen_commands: list[tuple[str, ...]] = []

    def fake_run_omx_command(
        arguments: tuple[str, ...] | list[str],
        cwd: str | None = None,
    ) -> OmxCommandResult:
        seen_commands.append(tuple(arguments))
        assert cwd == "/repo"
        return OmxCommandResult(
            exit_code=127,
            stdout="",
            stderr="No such file or directory: omx",
        )

    monkeypatch.setattr(
        "omx_remote.runtime.ultragoal.ultragoal_status.run_omx_command",
        fake_run_omx_command,
    )

    result = read_ultragoal_status(cwd="/repo")

    assert seen_commands == [("ultragoal", "--help")]
    assert result.supported is False
    assert result.state == UltragoalNativeState.UNAVAILABLE
    assert result.status_result is None
    assert result.warnings == ("omx ultragoal is not available.",)


def test_read_ultragoal_status_reports_status_failure_as_supported(
    monkeypatch,
) -> None:
    command_results = {
        ("ultragoal", "--help"): OmxCommandResult(
            exit_code=0,
            stdout="Usage: omx ultragoal ...",
            stderr="",
        ),
        ("ultragoal", "status", "--json"): OmxCommandResult(
            exit_code=1,
            stdout="No ultragoal plan found.",
            stderr="",
        ),
    }

    def fake_run_omx_command(
        arguments: tuple[str, ...] | list[str],
        cwd: str | None = None,
    ) -> OmxCommandResult:
        assert cwd is None
        return command_results[tuple(arguments)]

    monkeypatch.setattr(
        "omx_remote.runtime.ultragoal.ultragoal_status.run_omx_command",
        fake_run_omx_command,
    )

    result = read_ultragoal_status()

    assert result.supported is True
    assert result.state == UltragoalNativeState.STATUS_FAILED
    assert result.status_result is not None
    assert result.status_result.exit_code == 1
    assert result.warnings == ("omx ultragoal status returned a non-zero exit code.",)


def test_read_ultragoal_status_wraps_empty_status_stdout_without_traceback(
    monkeypatch,
) -> None:
    command_results = {
        ("ultragoal", "--help"): OmxCommandResult(
            exit_code=0,
            stdout="Usage: omx ultragoal ...",
            stderr="",
        ),
        ("ultragoal", "status", "--json"): OmxCommandResult(
            exit_code=0,
            stdout="",
            stderr="",
        ),
    }

    def fake_run_omx_command(
        arguments: tuple[str, ...] | list[str],
        cwd: str | None = None,
    ) -> OmxCommandResult:
        assert cwd == "/repo"
        return command_results[tuple(arguments)]

    monkeypatch.setattr(
        "omx_remote.runtime.ultragoal.ultragoal_status.run_omx_command",
        fake_run_omx_command,
    )

    result = read_ultragoal_status(cwd="/repo")

    assert result.supported is True
    assert result.state == UltragoalNativeState.AVAILABLE
    assert result.status_result is not None
    assert result.status_result.stdout == ""
    assert result.warnings == ()


def test_read_ultragoal_status_wraps_malformed_status_stdout_without_traceback(
    monkeypatch,
) -> None:
    command_results = {
        ("ultragoal", "--help"): OmxCommandResult(
            exit_code=0,
            stdout="Usage: omx ultragoal ...",
            stderr="",
        ),
        ("ultragoal", "status", "--json"): OmxCommandResult(
            exit_code=0,
            stdout="{not-json",
            stderr="",
        ),
    }

    def fake_run_omx_command(
        arguments: tuple[str, ...] | list[str],
        cwd: str | None = None,
    ) -> OmxCommandResult:
        return command_results[tuple(arguments)]

    monkeypatch.setattr(
        "omx_remote.runtime.ultragoal.ultragoal_status.run_omx_command",
        fake_run_omx_command,
    )

    result = read_ultragoal_status()

    assert result.supported is True
    assert result.state == UltragoalNativeState.AVAILABLE
    assert result.status_result is not None
    assert result.status_result.stdout == "{not-json"
