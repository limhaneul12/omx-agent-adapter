from pathlib import Path

from omx_remote.runtime.ralph.ralph_prd import (
    resolve_ralph_launch_task_from_prd,
    resolve_ralph_team_launch_task_from_prd,
    validate_ralph_launch_task,
    validate_ralph_prd_gate,
)
from omx_remote.runtime.ralph.ralph_state import (
    assess_ralph_launch_preflight_state,
    assess_ralph_resume_preflight_state,
    detect_tty_tmux_gate,
    require_ralph_launch_tty,
)
from omx_remote.runtime.ralph.ralph_team_handoff import (
    write_ralph_team_dag_handoff_artifacts,
)
from omx_remote.schemas.invoke.command_schemas import OmxCommandResult
from omx_remote.schemas.ralph.prd_schemas import RalphPrdArtifact
from omx_remote.shared.omx_enums.ralph_enums import RalphStateClassification


def launch_ralph_command(
    task: str,
    force_cleanup: bool,
    allow_non_tty: bool,
) -> list[str]:
    """Builds the Ralph launch command after preflight validation.

    Args:
        task [str]: Raw task text from the CLI.
        force_cleanup [bool]: Whether to proceed when stale state exists.
        allow_non_tty [bool]: Whether non-interactive launch is explicitly allowed.

    Returns:
        list[str]: OMX argv for the Ralph launch command.

    Raises:
        ValueError: If the task is blank or stale state exists without force.
    """
    launch_command, _warnings = build_ralph_launch_plan(
        task,
        force_cleanup=force_cleanup,
        allow_non_tty=allow_non_tty,
    )
    return launch_command


def build_ralph_launch_plan(
    task: str,
    force_cleanup: bool,
    allow_non_tty: bool,
) -> tuple[list[str], list[str]]:
    """Builds launch command and preflight warnings.

    Args:
        task [str]: Raw task text from CLI.
        force_cleanup [bool]: Whether to proceed when stale/running state exists.
        allow_non_tty [bool]: Whether non-interactive launch is explicitly allowed.

    Returns:
        tuple[list[str], list[str]]: Command plus preflight warnings.

    Raises:
        ValueError: If task is blank, TTY checks fail, PRD gate blocks, or stale active state blocks.
    """
    normalized_task: str = validate_ralph_launch_task(task)
    require_ralph_launch_tty(allow_non_tty=allow_non_tty)

    warnings: list[str] = []
    warnings.extend(detect_tty_tmux_gate(allow_non_tty, "Ralph"))
    ralph_prd_artifact: RalphPrdArtifact = validate_ralph_prd_gate()
    canonical_launch_task: str = resolve_ralph_launch_task_from_prd(
        task=normalized_task,
        ralph_prd_artifact=ralph_prd_artifact,
    )

    state_class, state_warnings = assess_ralph_launch_preflight_state()
    warnings.extend(state_warnings)

    if state_class == RalphStateClassification.RESUMABLE and not force_cleanup:
        raise ValueError(
            "Existing resumable Ralph state detected. Run `agent-remote ralph cleanup-stale` "
            "or retry with --force-cleanup."
        )

    launch_command: list[str] = ["ralph", "--prd", canonical_launch_task]
    return launch_command, warnings


def build_ralph_team_launch_plan(
    allow_non_tty: bool,
) -> tuple[list[str], list[str]]:
    """Builds Team launch command from the typed Ralph PRD artifact.

    Args:
        allow_non_tty [bool]: Whether non-interactive Team launch is explicitly allowed.

    Returns:
        tuple[list[str], list[str]]: Team launch command plus preflight warnings.
    """
    require_ralph_launch_tty(allow_non_tty=allow_non_tty)

    warnings: list[str] = []
    warnings.extend(detect_tty_tmux_gate(allow_non_tty, "Team"))
    ralph_prd_artifact: RalphPrdArtifact = validate_ralph_prd_gate()
    canonical_launch_task: str
    team_worker_count: int
    canonical_launch_task, team_worker_count = resolve_ralph_team_launch_task_from_prd(
        ralph_prd_artifact=ralph_prd_artifact,
    )
    write_ralph_team_dag_handoff_artifacts(
        ralph_prd_artifact=ralph_prd_artifact,
        canonical_launch_task=canonical_launch_task,
        team_worker_count=team_worker_count,
        workspace_root=Path.cwd(),
    )

    launch_command: list[str] = [
        "team",
        f"{team_worker_count}",
        canonical_launch_task,
    ]
    return launch_command, warnings


def resume_ralph_command() -> list[str]:
    """Builds the Ralph resume command after state preflight validation.

    Returns:
        list[str]: OMX argv for the Ralph resume command.

    Raises:
        ValueError: If no Ralph state exists to resume from.
    """
    state_class, _warnings = assess_ralph_resume_preflight_state()
    if state_class != RalphStateClassification.RESUMABLE:
        if state_class == RalphStateClassification.MISSING:
            raise ValueError(
                "No Ralph state found. Launch Ralph first or restore a resumable Ralph state."
            )
        raise ValueError("No resumable Ralph session found for ralph.")

    resume_command: list[str] = ["ralph"]
    return resume_command


def build_ralph_resume_plan() -> tuple[list[str], list[str]]:
    """Builds resume command and preflight warnings.

    Returns:
        tuple[list[str], list[str]]: Command plus resumability warnings.

    Raises:
        ValueError: If resume preflight fails.
    """
    state_class, warnings = assess_ralph_resume_preflight_state()
    if state_class != RalphStateClassification.RESUMABLE:
        if state_class == RalphStateClassification.MISSING:
            raise ValueError(
                "No Ralph state found. Launch Ralph first or restore a resumable Ralph state."
            )
        raise ValueError("No resumable Ralph session found for ralph.")

    resume_command: list[str] = ["ralph"]
    return resume_command, warnings


def format_resume_outcome(command_result: OmxCommandResult) -> OmxCommandResult:
    """Normalizes known Ralph resume non-resumable responses into a failure envelope.

    Args:
        command_result [OmxCommandResult]: Raw OMX command result.

    Returns:
        OmxCommandResult: Original result or a normalized preflight-style failure.
    """
    normalized_stdout: str = command_result.stdout.strip().lower()
    if command_result.exit_code == 0 and normalized_stdout == "no resumable team found for ralph":
        failure_result = format_preflight_failure(
            "No resumable Ralph session found. Launch Ralph first or restore a resumable Ralph runtime."
        )
        return failure_result

    return command_result


def format_preflight_failure(message: str) -> OmxCommandResult:
    """Returns a typed command result for Ralph preflight failures.

    Args:
        message [str]: Preflight failure detail.

    Returns:
        OmxCommandResult: Normalized failure envelope.
    """
    failure_result = OmxCommandResult(exit_code=2, stdout="", stderr=message)
    return failure_result
