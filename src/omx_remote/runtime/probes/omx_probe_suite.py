from omx_remote.runtime.probes.codex_probe_suite import _probe
from omx_remote.runtime.probes.probe_command_runner import (
    ProbeRunner,
    run_probe_command,
)
from omx_remote.schemas.probes.upstream_probe_schemas import (
    UpstreamProbeCommandResult,
    UpstreamProbeSuiteResult,
)

_OMX_PROBES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("version", ("omx", "--version")),
    ("help", ("omx", "--help")),
    ("ultragoal", ("omx", "ultragoal", "--help")),
    ("performance_goal", ("omx", "performance-goal", "--help")),
    ("autoresearch_goal", ("omx", "autoresearch-goal", "--help")),
    ("exec_json", ("omx", "exec", "--help")),
    ("state_json", ("omx", "state", "--help")),
    ("team", ("omx", "team", "--help")),
    ("team_api", ("omx", "team", "api", "--help")),
    ("adapt", ("omx", "adapt", "--help")),
)


def run_omx_probe_suite(runner: ProbeRunner = run_probe_command) -> UpstreamProbeSuiteResult:
    """Run the basic OMX upstream contract probe suite.

    Args:
        runner [ProbeRunner]: Probe runner dependency for tests or live probes.

    Returns:
        UpstreamProbeSuiteResult: OMX probe suite result.
    """
    results: tuple[UpstreamProbeCommandResult, ...] = tuple(
        _probe(capability, command, runner) for capability, command in _OMX_PROBES
    )
    suite = UpstreamProbeSuiteResult(
        suite_id="omx-basic",
        target="omx",
        results=results,
    )
    return suite
