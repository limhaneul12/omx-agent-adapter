import shutil
import subprocess
from collections.abc import Sequence

from omx_remote.schemas.cockpit.capability_snapshot_schemas import (
    CockpitCapabilitiesSnapshot,
    CockpitCapabilityCommand,
    CockpitRuntimeCapability,
)
from omx_remote.schemas.probes.upstream_probe_schemas import (
    ProbeSupportStatus,
    UpstreamProbeSuiteResult,
)

type CommandProbe = tuple[int, str, str]

_CODEX_COMMANDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("exec_json", ("exec", "--help")),
    ("mcp_server", ("mcp", "--help")),
    ("app_server", ("app", "--help")),
    ("remote_control", ("--help",)),
)
_OMX_COMMANDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ultragoal", ("ultragoal", "--help")),
    ("team", ("team", "--help")),
    ("ralph", ("ralph", "--help")),
    ("api", ("api", "--help")),
    ("performance-goal", ("performance-goal", "--help")),
    ("autoresearch-goal", ("autoresearch-goal", "--help")),
)


def _run_command(command: Sequence[str]) -> CommandProbe:
    """Run one read-only capability probe command.

    Args:
        command [Sequence[str]]: Command argv to execute.

    Returns:
        CommandProbe: Exit code, stdout, and stderr from the probe.
    """
    try:
        completed_process: subprocess.CompletedProcess[str] = subprocess.run(
            list(command),
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
    except OSError as error:
        probe: CommandProbe = (127, "", str(error))
        return probe
    except subprocess.TimeoutExpired as error:
        timeout_detail: str = str(error)
        probe = (124, "", timeout_detail)
        return probe

    stdout: str = "" if completed_process.stdout is None else completed_process.stdout
    stderr: str = "" if completed_process.stderr is None else completed_process.stderr
    probe = (completed_process.returncode, stdout, stderr)
    return probe


def _first_line(text: str) -> str | None:
    """Extract the first non-empty line from text.

    Args:
        text [str]: Text to inspect.

    Returns:
        str | None: First non-empty line when present.
    """
    for line in text.splitlines():
        stripped_line: str = line.strip()
        if stripped_line:
            first_line: str | None = stripped_line
            return first_line

    missing_line: None = None
    return missing_line


def _read_version(executable: str) -> str | None:
    """Read an executable version string.

    Args:
        executable [str]: Executable name or path.

    Returns:
        str | None: First version output line when available.
    """
    exit_code, stdout, stderr = _run_command((executable, "--version"))
    if exit_code != 0:
        missing_version: None = None
        return missing_version

    version: str | None = _first_line(stdout) or _first_line(stderr)
    return version


def _probe_command(executable: str, name: str, args: tuple[str, ...]) -> CockpitCapabilityCommand:
    """Probe one executable subcommand.

    Args:
        executable [str]: Executable name or path.
        name [str]: Capability name.
        args [tuple[str, ...]]: Probe arguments after the executable.

    Returns:
        CockpitCapabilityCommand: Command availability evidence.
    """
    exit_code, stdout, stderr = _run_command((executable, *args))
    output_detail: str = _first_line(stdout) or _first_line(stderr) or "no output"
    available: bool = exit_code == 0
    if available:
        detail: str = f"{executable} {' '.join(args)} succeeded: {output_detail}"
    else:
        detail = f"{executable} {' '.join(args)} failed with exit {exit_code}: {output_detail}"
    command = CockpitCapabilityCommand(
        name=name,
        available=available,
        detail=detail,
    )
    return command


def _runtime_capability(
    name: str,
    command_specs: tuple[tuple[str, tuple[str, ...]], ...],
) -> CockpitRuntimeCapability:
    """Build one runtime capability snapshot.

    Args:
        name [str]: Executable/runtime name.
        command_specs [tuple[tuple[str, tuple[str, ...]], ...]]: Command probes.

    Returns:
        CockpitRuntimeCapability: Runtime capability snapshot.
    """
    executable_path: str | None = shutil.which(name)
    if executable_path is None:
        capability = CockpitRuntimeCapability(
            name=name,
            available=False,
            executable_path=None,
            version=None,
            commands=(),
            warnings=(f"{name} executable was not found on PATH.",),
        )
        return capability

    commands: tuple[CockpitCapabilityCommand, ...] = tuple(
        _probe_command(name, command_name, args)
        for command_name, args in command_specs
    )
    capability = CockpitRuntimeCapability(
        name=name,
        available=True,
        executable_path=executable_path,
        version=_read_version(name),
        commands=commands,
        warnings=(),
    )
    return capability


def read_cockpit_capabilities() -> CockpitCapabilitiesSnapshot:
    """Read Codex and OMX capability evidence for cockpit snapshots.

    Returns:
        CockpitCapabilitiesSnapshot: Read-only capability evidence.
    """
    capabilities = CockpitCapabilitiesSnapshot(
        codex=_runtime_capability("codex", _CODEX_COMMANDS),
        omx=_runtime_capability("omx", _OMX_COMMANDS),
    )
    return capabilities


def runtime_capability_from_probe_suite(
    name: str,
    suite_result: UpstreamProbeSuiteResult,
) -> CockpitRuntimeCapability:
    """Build a cockpit runtime capability snapshot from probe evidence.

    Args:
        name [str]: Runtime name.
        suite_result [UpstreamProbeSuiteResult]: Probe suite evidence.

    Returns:
        CockpitRuntimeCapability: Capability snapshot derived from probes.
    """
    commands: tuple[CockpitCapabilityCommand, ...] = tuple(
        CockpitCapabilityCommand(
            name=result.capability,
            available=result.support_status == ProbeSupportStatus.SUPPORTED,
            detail=result.stdout_summary or result.stderr_summary or "no probe output",
        )
        for result in suite_result.results
    )
    runtime_capability = CockpitRuntimeCapability(
        name=name,
        available=any(command.available for command in commands),
        executable_path=None,
        version=None,
        commands=commands,
        warnings=(),
    )
    return runtime_capability
