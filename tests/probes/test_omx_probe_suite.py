from omx_remote.runtime.probes.omx_probe_suite import run_omx_probe_suite
from omx_remote.runtime.cockpit.sources.capability_snapshot import (
    runtime_capability_from_probe_suite,
)
from omx_remote.schemas.upstream_probe_schemas import (
    ProbeProcessOutput,
    ProbeSupportStatus,
)


def test_omx_probe_suite_marks_available_and_missing_commands() -> None:
    def fake_runner(command: tuple[str, ...]) -> ProbeProcessOutput:
        if command in {
            ("omx", "--version"),
            ("omx", "ultragoal", "--help"),
            ("omx", "team", "--help"),
        }:
            return ProbeProcessOutput(exit_code=0, stdout="ok\n", stderr="")
        return ProbeProcessOutput(exit_code=2, stdout="", stderr="unknown")

    result = run_omx_probe_suite(fake_runner)
    result_by_capability = {probe.capability: probe for probe in result.results}

    assert (
        result_by_capability["version"].support_status == ProbeSupportStatus.SUPPORTED
    )
    assert (
        result_by_capability["ultragoal"].support_status == ProbeSupportStatus.SUPPORTED
    )
    assert result_by_capability["team"].support_status == ProbeSupportStatus.SUPPORTED
    assert (
        result_by_capability["performance_goal"].support_status
        == ProbeSupportStatus.UNSUPPORTED
    )
    assert result.supported_count == 3

    capability = runtime_capability_from_probe_suite("omx", result)

    assert capability.available is True
    assert capability.commands[0].name == "version"
    assert capability.commands[0].available is True
