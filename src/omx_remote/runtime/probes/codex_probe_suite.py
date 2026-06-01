import orjson

from omx_remote.adapter_types.json_types import (
    JsonArray,
    JsonObject,
    JsonScalar,
    JsonValue,
)
from omx_remote.runtime.probes.probe_command_runner import (
    ProbeRunner,
    run_probe_command,
)
from omx_remote.schemas.upstream_probe_schemas import (
    ProbeProcessOutput,
    ProbeSupportStatus,
    UpstreamProbeCommandResult,
    UpstreamProbeSuiteResult,
)

_CODEX_PROBES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("version", ("codex", "--version")),
    ("features_json", ("codex", "features", "list", "--json")),
    ("exec_json", ("codex", "exec", "--help")),
    ("exec_output_schema", ("codex", "exec", "--output-schema", "--help")),
    ("plugin_help", ("codex", "plugin", "--help")),
    ("mcp_server", ("codex", "mcp-server", "--help")),
    ("app_server", ("codex", "app-server", "--help")),
)


def _summary(text: str) -> str:
    """Return the first non-empty output line.

    Args:
        text [str]: Output text to summarize.

    Returns:
        str: First non-empty line or empty string.
    """
    for line in text.splitlines():
        stripped_line: str = line.strip()
        if stripped_line:
            summary_text: str = stripped_line
            return summary_text

    empty_summary: str = ""
    return empty_summary


def _support_status(output: ProbeProcessOutput) -> ProbeSupportStatus:
    """Derive support status from process output.

    Args:
        output [ProbeProcessOutput]: Captured process output.

    Returns:
        ProbeSupportStatus: Derived support status.
    """
    if output.exit_code == 0:
        status: ProbeSupportStatus = ProbeSupportStatus.SUPPORTED
        return status
    if output.exit_code == 124:
        status = ProbeSupportStatus.UNKNOWN
        return status

    status = ProbeSupportStatus.UNSUPPORTED
    return status


def _as_json_value(value: object) -> JsonValue | None:
    """Normalize a parsed object to the shared JSON value alias.

    Args:
        value [object]: Parsed JSON candidate.

    Returns:
        JsonValue | None: JSON value when the candidate matches supported JSON types.
    """
    if value is None or isinstance(value, str | int | float | bool):
        scalar: JsonScalar = value
        return scalar
    if isinstance(value, list):
        items: JsonArray = []
        for item in value:
            json_item: JsonValue | None = _as_json_value(item)
            if json_item is None and item is not None:
                missing_value: None = None
                return missing_value
            items.append(json_item)
        return items
    if isinstance(value, dict):
        result_object: JsonObject = {}
        for key, item in value.items():
            if not isinstance(key, str):
                missing_value = None
                return missing_value
            json_item = _as_json_value(item)
            if json_item is None and item is not None:
                missing_value = None
                return missing_value
            result_object[key] = json_item
        return result_object

    missing_value = None
    return missing_value


def _parsed_json(stdout: str) -> JsonValue | None:
    """Parse JSON stdout when available.

    Args:
        stdout [str]: Stdout text.

    Returns:
        JsonValue | None: Parsed JSON value or ``None``.
    """
    try:
        parsed: object = orjson.loads(stdout)
    except orjson.JSONDecodeError:
        missing_json: None = None
        return missing_json

    parsed_json: JsonValue | None = _as_json_value(parsed)
    return parsed_json


def _probe(
    capability: str, command: tuple[str, ...], runner: ProbeRunner
) -> UpstreamProbeCommandResult:
    """Run one Codex contract probe.

    Args:
        capability [str]: Capability name.
        command [tuple[str, ...]]: Probe command argv.
        runner [ProbeRunner]: Probe runner dependency.

    Returns:
        UpstreamProbeCommandResult: Normalized probe result.
    """
    output: ProbeProcessOutput = runner(command)
    result = UpstreamProbeCommandResult(
        capability=capability,
        command=command,
        exit_code=output.exit_code,
        stdout_summary=_summary(output.stdout),
        stderr_summary=_summary(output.stderr),
        parsed_json=_parsed_json(output.stdout),
        support_status=_support_status(output),
    )
    return result


def run_codex_probe_suite(
    runner: ProbeRunner = run_probe_command,
) -> UpstreamProbeSuiteResult:
    """Run the basic Codex upstream contract probe suite.

    Args:
        runner [ProbeRunner]: Probe runner dependency for tests or live probes.

    Returns:
        UpstreamProbeSuiteResult: Codex probe suite result.
    """
    results: tuple[UpstreamProbeCommandResult, ...] = tuple(
        _probe(capability, command, runner) for capability, command in _CODEX_PROBES
    )
    suite = UpstreamProbeSuiteResult(
        suite_id="codex-basic",
        target="codex",
        results=results,
    )
    return suite
