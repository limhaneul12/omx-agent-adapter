from __future__ import annotations

import sys
from pathlib import Path

from omx_remote.schemas.invoke_schemas import OmxCommandResult

_RALPH_STATE_FILENAMES: tuple[str, ...] = (
    "ralph-state.json",
    "ralph-progress.json",
    "run-state.json",
)


def get_ralph_state_root(workspace_root: Path | None = None) -> Path:
    """Return the OMX state directory for the current workspace.

    Args:
        workspace_root [Path | None]: Optional explicit workspace root.

    Returns:
        Path: The `.omx/state` directory path for the workspace.
    """
    resolved_workspace_root: Path
    if workspace_root is None:
        resolved_workspace_root = Path.cwd()
    else:
        resolved_workspace_root = workspace_root

    state_root: Path = resolved_workspace_root / ".omx" / "state"
    return state_root


def list_ralph_state_paths(workspace_root: Path | None = None) -> list[Path]:
    """List known Ralph state paths that currently exist.

    Args:
        workspace_root [Path | None]: Optional explicit workspace root.

    Returns:
        list[Path]: Existing known Ralph state files.
    """
    state_root: Path = get_ralph_state_root(workspace_root=workspace_root)
    existing_state_paths: list[Path] = []

    relative_name: str
    for relative_name in _RALPH_STATE_FILENAMES:
        state_path: Path = state_root / relative_name
        if state_path.exists():
            existing_state_paths.append(state_path)

    return existing_state_paths


def require_ralph_launch_tty(*, allow_non_tty: bool) -> None:
    """Validate whether Ralph launch may proceed in the current stdin mode.

    Args:
        allow_non_tty [bool]: Whether non-interactive launch is explicitly allowed.

    Raises:
        ValueError: If stdin is not a TTY and non-interactive launch was not allowed.
    """
    if allow_non_tty:
        return

    if not sys.stdin.isatty():
        raise ValueError(
            "Ralph launch requires an interactive TTY. Retry from a terminal or pass --allow-non-tty."
        )


def validate_ralph_launch_task(task: str) -> str:
    """Normalize and validate task text for Ralph launch.

    Args:
        task [str]: Raw task text from the CLI.

    Returns:
        str: Stripped non-blank task text.

    Raises:
        ValueError: If the task text is blank after stripping.
    """
    normalized_task: str = task.strip()
    if normalized_task == "":
        raise ValueError("Task text must not be blank.")

    return normalized_task


def launch_ralph_command(
    task: str,
    *,
    force_cleanup: bool,
    allow_non_tty: bool,
) -> list[str]:
    """Build the Ralph launch command after preflight validation.

    Args:
        task [str]: Raw task text from the CLI.
        force_cleanup [bool]: Whether to proceed when stale state exists.
        allow_non_tty [bool]: Whether non-interactive launch is explicitly allowed.

    Returns:
        list[str]: OMX argv for the Ralph launch command.

    Raises:
        ValueError: If the task is blank or stale state exists without force.
    """
    normalized_task: str = validate_ralph_launch_task(task)
    require_ralph_launch_tty(allow_non_tty=allow_non_tty)
    existing_state_paths: list[Path] = list_ralph_state_paths()
    if existing_state_paths and not force_cleanup:
        joined_paths: str = ", ".join(str(path) for path in existing_state_paths)
        raise ValueError(
            "Existing Ralph state detected. Run `agent-remote ralph cleanup-stale` "
            f"or retry with --force-cleanup. Paths: {joined_paths}"
        )

    launch_command: list[str] = ["ralph", "--prd", normalized_task]
    return launch_command


def resume_ralph_command() -> list[str]:
    """Build the Ralph resume command after state preflight validation.

    Returns:
        list[str]: OMX argv for the Ralph resume command.

    Raises:
        ValueError: If no Ralph state exists to resume from.
    """
    existing_state_paths: list[Path] = list_ralph_state_paths()
    if not existing_state_paths:
        raise ValueError(
            "No Ralph state found. Launch Ralph first or restore the Ralph state files."
        )

    resume_command: list[str] = ["ralph"]
    return resume_command


def cleanup_ralph_state(workspace_root: Path | None = None) -> list[str]:
    """Remove known Ralph stale-state files.

    Args:
        workspace_root [Path | None]: Optional explicit workspace root.

    Returns:
        list[str]: Removed file paths as strings.
    """
    existing_state_paths: list[Path] = list_ralph_state_paths(workspace_root=workspace_root)
    removed_paths: list[str] = []

    state_path: Path
    for state_path in existing_state_paths:
        state_path.unlink()
        removed_paths.append(str(state_path))

    return removed_paths


def format_resume_outcome(command_result: OmxCommandResult) -> OmxCommandResult:
    """Normalize known Ralph resume non-resumable responses into a failure envelope.

    Args:
        command_result [OmxCommandResult]: Raw OMX command result.

    Returns:
        OmxCommandResult: Original result or a normalized preflight-style failure.
    """
    normalized_stdout: str = command_result.stdout.strip().lower()
    if (
        command_result.exit_code == 0
        and normalized_stdout == "no resumable team found for ralph"
    ):
        failure_result = format_preflight_failure(
            "No resumable Ralph session found. Launch Ralph first or restore a resumable Ralph runtime."
        )
        return failure_result

    return command_result


def format_preflight_failure(message: str) -> OmxCommandResult:
    """Return a typed command result for Ralph preflight failures.

    Args:
        message [str]: Preflight failure detail.

    Returns:
        OmxCommandResult: Normalized failure envelope.
    """
    failure_result = OmxCommandResult(exit_code=2, stdout="", stderr=message)
    return failure_result
