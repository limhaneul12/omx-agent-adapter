from __future__ import annotations

import json
import sys
from pathlib import Path
from shutil import which
from typing import Any

from omx_remote.schemas.invoke_schemas import OmxCommandResult

_RALPH_STATE_FILENAMES: tuple[str, ...] = (
    "ralph-state.json",
    "ralph-progress.json",
    "run-state.json",
)
_TERMINAL_PHASES: frozenset[str] = frozenset(
    {"complete", "completed", "failed", "cancelled"}
)
_NON_TERMINAL_PHASES: frozenset[str] = frozenset(
    {
        "starting",
        "running",
        "executing",
        "planning",
        "active",
        "paused",
        "idle",
        "userinterlude",
        "blocked_on_user",
        "waiting",
    }
)
_TERMINAL_OUTCOMES: frozenset[str] = frozenset(
    {
        "finish",
        "blocked_on_user",
        "failed",
        "cancelled",
        "complete",
        "completed",
        "done",
        "userinterlude",
    }
)
_NON_TERMINAL_OUTCOMES: frozenset[str] = frozenset(
    {"continue", "progress", "running", "active"}
)


def _normalize_token(value: object) -> str | None:
    token: str
    if not isinstance(value, str):
        return None

    token = value.strip().lower()
    return token or None


def _read_json_object(path: Path) -> dict[str, Any] | None:
    try:
        raw_payload: str = path.read_text(encoding="utf-8")
    except OSError:
        return None

    parsed_payload: object
    try:
        parsed_payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        return None

    if isinstance(parsed_payload, dict):
        return parsed_payload

    return None


def _is_terminal_ralph_phase(phase_value: object) -> bool:
    phase: str | None = _normalize_token(phase_value)
    return bool(phase and phase in _TERMINAL_PHASES)


def _is_terminal_ralph_outcome(outcome_value: object) -> bool:
    outcome: str | None = _normalize_token(outcome_value)
    return bool(outcome and outcome in _TERMINAL_OUTCOMES)


def _is_active_ralph_phase(phase_value: object) -> bool:
    phase: str | None = _normalize_token(phase_value)
    return bool(phase and phase in _NON_TERMINAL_PHASES)


def _is_active_ralph_outcome(outcome_value: object) -> bool:
    outcome: str | None = _normalize_token(outcome_value)
    return bool(outcome and outcome in _NON_TERMINAL_OUTCOMES)


def _classify_ralph_state_snapshot(state_payload: dict[str, Any]) -> str:
    """Classify Ralph state as resumable / terminal / stale."""
    active_value: object | None = state_payload.get("active")

    if active_value is True:
        return "resumable"

    if active_value is False:
        outcome_value: object | None = state_payload.get("run_outcome")
        if outcome_value is None:
            outcome_value = state_payload.get("outcome")

        if _is_terminal_ralph_outcome(outcome_value):
            return "terminal"

        phase_value: object | None = state_payload.get("current_phase")
        if _is_terminal_ralph_phase(phase_value):
            return "terminal"

        if _is_active_ralph_outcome(outcome_value) or _is_active_ralph_phase(phase_value):
            return "resumable"

        return "stale"

    if active_value is not None and not isinstance(active_value, bool):
        return "stale"

    outcome_value: object | None = state_payload.get("run_outcome")
    if outcome_value is None:
        outcome_value = state_payload.get("outcome")

    phase_value: object | None = state_payload.get("current_phase")

    if _is_terminal_ralph_outcome(outcome_value):
        return "terminal"

    if _is_active_ralph_outcome(outcome_value) or _is_active_ralph_phase(phase_value):
        return "resumable"

    if _is_terminal_ralph_phase(phase_value):
        return "terminal"

    return "stale"


def _assess_ralph_launch_preflight_state() -> tuple[str, list[str]]:
    existing_state_paths: list[Path] = list_ralph_state_paths()
    if not existing_state_paths:
        return "clean", []

    ralph_state_path: Path = get_ralph_state_root() / "ralph-state.json"
    if ralph_state_path not in existing_state_paths:
        joined_paths: str = ", ".join(str(path) for path in existing_state_paths)
        return "stale", [
            "Existing Ralph state files were found, but no ralph-state.json was present.",
            f"Known stale files: {joined_paths}",
            "If these are stale, run `agent-remote ralph cleanup-stale` before re-launching.",
        ]

    ralph_state_payload: dict[str, Any] | None = _read_json_object(ralph_state_path)
    if ralph_state_payload is None:
        joined_paths: str = ", ".join(str(path) for path in existing_state_paths)
        return "terminal", [
            "Ralph state artifact is present but unreadable.",
            f"Paths: {joined_paths}",
            "Clean stale Ralph artifacts and retry with `agent-remote ralph cleanup-stale`.",
        ]

    state_class: str = _classify_ralph_state_snapshot(ralph_state_payload)
    joined_paths = ", ".join(str(path) for path in existing_state_paths)

    if state_class == "resumable":
        return "resumable", [
            "Ralph appears resumable from existing state.",
            f"Paths: {joined_paths}",
            "If you intend to start a new session, run `agent-remote ralph cleanup-stale` or use --force-cleanup.",
        ]

    if state_class == "terminal":
        return "terminal", [
            "Ralph state exists and is terminal/non-runnable.",
            f"Paths: {joined_paths}",
            "Proceeding is treated as a stale-state recovery path.",
        ]

    return "stale", [
        "Ralph state exists but lacks explicit resumability markers.",
        f"Paths: {joined_paths}",
        "Proceeding may overwrite stale artifacts unless you run cleanup first.",
    ]


def _assess_ralph_resume_preflight_state() -> tuple[str, list[str]]:
    existing_state_paths: list[Path] = list_ralph_state_paths()
    if not existing_state_paths:
        return "missing", ["No Ralph state files found."]

    ralph_state_path = get_ralph_state_root() / "ralph-state.json"
    if not ralph_state_path.exists():
        joined_paths: str = ", ".join(str(path) for path in existing_state_paths)
        return "invalid", [
            "Ralph state exists without a canonical ralph-state.json.",
            f"Known Ralph files: {joined_paths}",
            "Run cleanup-stale and re-run launch if this is stale recovery.",
        ]

    state_payload: dict[str, Any] | None = _read_json_object(ralph_state_path)
    if state_payload is None:
        return "invalid", [
            "Ralph state file is present but unreadable.",
            f"Path: {ralph_state_path}",
        ]

    state_class: str = _classify_ralph_state_snapshot(state_payload)
    if state_class != "resumable":
        return state_class, [
            f"Ralph state file class is '{state_class}'.",
            "Resume requires an active or non-terminal Ralph state.",
        ]

    warnings: list[str] = ["Ralph state classified as resumable."]
    ralph_progress_path = get_ralph_state_root() / "ralph-progress.json"
    if not ralph_progress_path.exists():
        warnings.append("Ralph progress artifact is missing; resume may lose progress history.")

    return "resumable", warnings


def _validate_ralph_prd_gate() -> None:
    prd_path: Path = Path.cwd() / ".omx" / "prd.json"
    if not prd_path.exists():
        raise ValueError(
            "Missing required PRD.json at .omx/prd.json. Create the file before running `agent-remote ralph launch`."
        )

    prd_payload: dict[str, Any] | None = _read_json_object(prd_path)
    if prd_payload is None:
        raise ValueError("Invalid or unreadable .omx/prd.json: expected JSON object.")

    _ = prd_payload


def _detect_tty_tmux_gate(*, allow_non_tty: bool) -> list[str]:
    warnings: list[str] = []
    if which("tmux") is None:
        warnings.append(
            "tmux was not detected. Ralph runs in direct mode without detached tmux HUD. "
            "Install tmux for the normal launch UX."
        )

    if allow_non_tty:
        warnings.append(
            "allow-non-tty is enabled; launch behavior may differ from interactive-tty mode."
        )

    return warnings


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
    launch_command, _warnings = build_ralph_launch_plan(
        task,
        force_cleanup=force_cleanup,
        allow_non_tty=allow_non_tty,
    )
    return launch_command


def build_ralph_launch_plan(
    task: str,
    *,
    force_cleanup: bool,
    allow_non_tty: bool,
) -> tuple[list[str], list[str]]:
    """Build launch command and preflight warnings.

    Args:
        task [str]: Raw task text from CLI.
        force_cleanup [bool]: Whether to proceed when stale/running state exists.
        allow_non_tty [bool]: Whether non-interactive launch is explicitly allowed.

    Returns:
        tuple[list[str], list[str]]: Command plus preflight warnings.

    Raises:
        ValueError: If task is blank, TTY/timer checks fail, PRD gate blocks, or stale active state blocks.
    """
    normalized_task: str = validate_ralph_launch_task(task)
    require_ralph_launch_tty(allow_non_tty=allow_non_tty)

    warnings: list[str] = []
    warnings.extend(_detect_tty_tmux_gate(allow_non_tty=allow_non_tty))
    _validate_ralph_prd_gate()

    state_class, state_warnings = _assess_ralph_launch_preflight_state()
    warnings.extend(state_warnings)

    if state_class == "resumable" and not force_cleanup:
        raise ValueError(
            "Existing resumable Ralph state detected. Run `agent-remote ralph cleanup-stale` "
            "or retry with --force-cleanup."
        )

    launch_command: list[str] = ["ralph", "--prd", normalized_task]
    return launch_command, warnings


def resume_ralph_command() -> list[str]:
    """Build the Ralph resume command after state preflight validation.

    Returns:
        list[str]: OMX argv for the Ralph resume command.

    Raises:
        ValueError: If no Ralph state exists to resume from.
    """
    state_class, _warnings = _assess_ralph_resume_preflight_state()
    if state_class != "resumable":
        if state_class == "missing":
            raise ValueError(
                "No Ralph state found. Launch Ralph first or restore a resumable Ralph state."
            )
        raise ValueError("No resumable Ralph session found for ralph.")

    resume_command: list[str] = ["ralph"]
    return resume_command


def build_ralph_resume_plan() -> tuple[list[str], list[str]]:
    """Build resume command and preflight warnings.

    Returns:
        tuple[list[str], list[str]]: Command plus resumability warnings.

    Raises:
        ValueError: If resume preflight fails.
    """
    state_class, warnings = _assess_ralph_resume_preflight_state()
    if state_class != "resumable":
        if state_class == "missing":
            raise ValueError(
                "No Ralph state found. Launch Ralph first or restore a resumable Ralph state."
            )
        raise ValueError("No resumable Ralph session found for ralph.")

    resume_command: list[str] = ["ralph"]
    return resume_command, warnings


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
