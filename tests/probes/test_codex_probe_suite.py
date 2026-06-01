from omx_remote.runtime.probes.codex_probe_suite import run_codex_probe_suite
from omx_remote.schemas.upstream_probe_schemas import (
    ProbeProcessOutput,
    ProbeSupportStatus,
)


def test_codex_probe_suite_uses_fake_runner_without_shelling_out() -> None:
    calls: list[tuple[str, ...]] = []

    def fake_runner(command: tuple[str, ...]) -> ProbeProcessOutput:
        calls.append(command)
        if command == ("codex", "--version"):
            return ProbeProcessOutput(exit_code=0, stdout="codex 0.133.0\n", stderr="")
        if command == ("codex", "exec", "--help"):
            return ProbeProcessOutput(
                exit_code=0, stdout="Usage: codex exec --json\n", stderr=""
            )
        return ProbeProcessOutput(exit_code=1, stdout="", stderr="unknown command")

    result = run_codex_probe_suite(fake_runner)

    result_by_capability = {probe.capability: probe for probe in result.results}

    assert ("codex", "--version") in calls
    assert (
        result_by_capability["version"].support_status == ProbeSupportStatus.SUPPORTED
    )
    assert (
        result_by_capability["exec_json"].support_status == ProbeSupportStatus.SUPPORTED
    )
    assert (
        result_by_capability["plugin_help"].support_status
        == ProbeSupportStatus.UNSUPPORTED
    )
    assert result.supported_count == 2


def test_codex_probe_parses_json_stdout_when_available() -> None:
    def fake_runner(command: tuple[str, ...]) -> ProbeProcessOutput:
        if command == ("codex", "features", "list", "--json"):
            return ProbeProcessOutput(
                exit_code=0,
                stdout='{"features":["goals","subagents"]}',
                stderr="",
            )
        return ProbeProcessOutput(exit_code=1, stdout="", stderr="missing")

    result = run_codex_probe_suite(fake_runner)
    features_probe = next(
        probe for probe in result.results if probe.capability == "features_json"
    )

    assert features_probe.parsed_json == {"features": ["goals", "subagents"]}
    assert features_probe.support_status == ProbeSupportStatus.SUPPORTED
