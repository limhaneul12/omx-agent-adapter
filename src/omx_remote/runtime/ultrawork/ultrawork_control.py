from __future__ import annotations

import sys
from pathlib import Path
from shutil import which

from omx_remote.adapter_types.type_contract.ultrawork_contract_type import (
    ULTRAWORK_NON_TERMINAL_OUTCOMES,
    ULTRAWORK_NON_TERMINAL_PHASES,
    ULTRAWORK_TERMINAL_OUTCOMES,
    ULTRAWORK_TERMINAL_PHASES,
)
from omx_remote.schemas.invoke.command_schemas import OmxCommandResult
from omx_remote.shared.omx_enums.ultrawork_enums import (
    UltraworkRunOutcome,
    UltraworkRuntimePhase,
    UltraworkStateClassification,
)
from omx_remote.shared.utils.json_file_store import json_file_stores

_ULTRAWORK_STATE_FILENAMES: tuple[str, ...] = (
    "ultrawork-state.json",
    "ultrawork-progress.json",
    "run-state.json",
)


def _normalize_token(value: object) -> str | None:
    """Handles normalize token.
    
    Args:
        value [object]: Function argument.
    
    Returns:
        str | None: Function return value.
    """
    token: str
    if not isinstance(value, str):
        return None

    token = value.strip().lower()
    normalized_token: str | None = token or None
    return normalized_token


class UltraworkStateClassifier:
    """Classifies adapter-visible Ultrawork runtime state markers."""

    @staticmethod
    def normalize_phase(phase_value: object) -> UltraworkRuntimePhase | None:
        """Normalize a raw phase marker into an Ultrawork phase enum.

        Args:
            phase_value: Raw phase value read from an Ultrawork state artifact.

        Returns:
            Matching Ultrawork phase enum, or ``None`` when unknown.
        """
        token: str | None = _normalize_token(phase_value)
        if token is None:
            return None

        try:
            phase = UltraworkRuntimePhase(token)
        except ValueError:
            return None

        return phase

    @staticmethod
    def normalize_outcome(outcome_value: object) -> UltraworkRunOutcome | None:
        """Normalize a raw outcome marker into an Ultrawork outcome enum.

        Args:
            outcome_value: Raw outcome value read from an Ultrawork state artifact.

        Returns:
            Matching Ultrawork outcome enum, or ``None`` when unknown.
        """
        token: str | None = _normalize_token(outcome_value)
        if token is None:
            return None

        try:
            outcome = UltraworkRunOutcome(token)
        except ValueError:
            return None

        return outcome

    @staticmethod
    def is_terminal_phase(phase_value: object) -> bool:
        """Return whether a raw phase value is terminal.

        Args:
            phase_value: Raw phase value read from state.

        Returns:
            ``True`` when the phase maps to a terminal Ultrawork phase.
        """
        phase: UltraworkRuntimePhase | None = UltraworkStateClassifier.normalize_phase(
            phase_value
        )
        is_terminal_phase = bool(
            phase and phase in ULTRAWORK_TERMINAL_PHASES
        )
        return is_terminal_phase

    @staticmethod
    def is_terminal_outcome(outcome_value: object) -> bool:
        """Return whether a raw outcome value is terminal.

        Args:
            outcome_value: Raw outcome value read from state.

        Returns:
            ``True`` when the outcome maps to a terminal Ultrawork outcome.
        """
        outcome: UltraworkRunOutcome | None = UltraworkStateClassifier.normalize_outcome(
            outcome_value
        )
        is_terminal_outcome = bool(
            outcome and outcome in ULTRAWORK_TERMINAL_OUTCOMES
        )
        return is_terminal_outcome

    @staticmethod
    def is_active_phase(phase_value: object) -> bool:
        """Return whether a raw phase value is resumable/non-terminal.

        Args:
            phase_value: Raw phase value read from state.

        Returns:
            ``True`` when the phase maps to a non-terminal Ultrawork phase.
        """
        phase: UltraworkRuntimePhase | None = UltraworkStateClassifier.normalize_phase(
            phase_value
        )
        is_active_phase = bool(phase and phase in ULTRAWORK_NON_TERMINAL_PHASES)
        return is_active_phase

    @staticmethod
    def is_active_outcome(outcome_value: object) -> bool:
        """Return whether a raw outcome value is resumable/non-terminal.

        Args:
            outcome_value: Raw outcome value read from state.

        Returns:
            ``True`` when the outcome maps to a non-terminal Ultrawork outcome.
        """
        outcome: UltraworkRunOutcome | None = UltraworkStateClassifier.normalize_outcome(
            outcome_value
        )
        is_active_outcome = bool(
            outcome and outcome in ULTRAWORK_NON_TERMINAL_OUTCOMES
        )
        return is_active_outcome

    @staticmethod
    def classify_state_snapshot(
        state_payload: dict[str, object],
    ) -> UltraworkStateClassification:
        """Classify one Ultrawork state payload for launch/resume preflight.

        Args:
            state_payload: Parsed Ultrawork state object.

        Returns:
            Adapter-owned Ultrawork state classification.
        """
        active_value: object | None = state_payload.get("active")

        if active_value is True:
            return UltraworkStateClassification.RESUMABLE

        if active_value is False:
            classification = UltraworkStateClassifier._classify_inactive_state(
                state_payload
            )
            return classification

        if active_value is not None and not isinstance(active_value, bool):
            return UltraworkStateClassification.STALE

        classification = UltraworkStateClassifier._classify_marker_state(state_payload)
        return classification

    @staticmethod
    def _classify_inactive_state(
        state_payload: dict[str, object],
    ) -> UltraworkStateClassification:
        """Handles classify inactive state.
        
        Args:
            state_payload [dict[str, object]]: Function argument.
        
        Returns:
            UltraworkStateClassification: Function return value.
        """
        outcome_value: object | None = UltraworkStateClassifier._read_outcome_value(
            state_payload
        )
        phase_value: object | None = state_payload.get("current_phase")

        if UltraworkStateClassifier.is_terminal_outcome(
            outcome_value
        ) or UltraworkStateClassifier.is_terminal_phase(phase_value):
            return UltraworkStateClassification.TERMINAL

        if UltraworkStateClassifier.is_active_outcome(
            outcome_value
        ) or UltraworkStateClassifier.is_active_phase(phase_value):
            return UltraworkStateClassification.RESUMABLE

        return UltraworkStateClassification.STALE

    @staticmethod
    def _classify_marker_state(
        state_payload: dict[str, object],
    ) -> UltraworkStateClassification:
        """Handles classify marker state.
        
        Args:
            state_payload [dict[str, object]]: Function argument.
        
        Returns:
            UltraworkStateClassification: Function return value.
        """
        outcome_value: object | None = UltraworkStateClassifier._read_outcome_value(
            state_payload
        )
        phase_value: object | None = state_payload.get("current_phase")

        if UltraworkStateClassifier.is_terminal_outcome(outcome_value):
            return UltraworkStateClassification.TERMINAL

        if UltraworkStateClassifier.is_active_outcome(
            outcome_value
        ) or UltraworkStateClassifier.is_active_phase(phase_value):
            return UltraworkStateClassification.RESUMABLE

        if UltraworkStateClassifier.is_terminal_phase(phase_value):
            return UltraworkStateClassification.TERMINAL

        return UltraworkStateClassification.STALE

    @staticmethod
    def _read_outcome_value(state_payload: dict[str, object]) -> object | None:
        """Handles read outcome value.
        
        Args:
            state_payload [dict[str, object]]: Function argument.
        
        Returns:
            object | None: Function return value.
        """
        outcome_value: object | None = state_payload.get("run_outcome")
        if outcome_value is None:
            outcome_value = state_payload.get("outcome")

        return outcome_value


def _classify_ultrawork_state_snapshot(
    state_payload: dict[str, object],
) -> UltraworkStateClassification:
    """Handles classify ultrawork state snapshot.
    
    Args:
        state_payload [dict[str, object]]: Function argument.
    
    Returns:
        UltraworkStateClassification: Function return value.
    """
    classification: UltraworkStateClassification = (
        UltraworkStateClassifier.classify_state_snapshot(state_payload)
    )
    return classification


def _assess_ultrawork_launch_preflight_state() -> tuple[UltraworkStateClassification, list[str]]:
    """Handles assess ultrawork launch preflight state.
    
    Returns:
        tuple[UltraworkStateClassification, list[str]]: Function return value.
    """
    existing_state_paths: list[Path] = list_ultrawork_state_paths()
    if not existing_state_paths:
        return UltraworkStateClassification.CLEAN, []

    ultrawork_state_path: Path = get_ultrawork_state_root() / "ultrawork-state.json"
    if ultrawork_state_path not in existing_state_paths:
        joined_paths: str = ", ".join(str(path) for path in existing_state_paths)
        return UltraworkStateClassification.STALE, [
            "Existing Ultrawork state files were found, but no ultrawork-state.json was present.",
            f"Known stale files: {joined_paths}",
            "If these are stale, run `agent-remote ultrawork cleanup-stale` before re-launching.",
        ]

    ultrawork_state_store = json_file_stores.for_path(ultrawork_state_path)
    ultrawork_state_payload: dict[str, object] | None = ultrawork_state_store.read_object()
    if ultrawork_state_payload is None:
        joined_paths: str = ", ".join(str(path) for path in existing_state_paths)
        return UltraworkStateClassification.TERMINAL, [
            "Ultrawork state artifact is present but unreadable.",
            f"Paths: {joined_paths}",
            "Clean stale Ultrawork artifacts and retry with `agent-remote ultrawork cleanup-stale`.",
        ]

    state_class: str = _classify_ultrawork_state_snapshot(ultrawork_state_payload)
    joined_paths = ", ".join(str(path) for path in existing_state_paths)

    if state_class == UltraworkStateClassification.RESUMABLE:
        return UltraworkStateClassification.RESUMABLE, [
            "Ultrawork appears resumable from existing state.",
            f"Paths: {joined_paths}",
            "If you intend to start a new session, run `agent-remote ultrawork cleanup-stale` or use --force-cleanup.",
        ]

    if state_class == UltraworkStateClassification.TERMINAL:
        return UltraworkStateClassification.TERMINAL, [
            "Ultrawork state exists and is terminal/non-runnable.",
            f"Paths: {joined_paths}",
            "Proceeding is treated as a stale-state recovery path.",
        ]

    return UltraworkStateClassification.STALE, [
        "Ultrawork state exists but lacks explicit resumability markers.",
        f"Paths: {joined_paths}",
        "Proceeding may overwrite stale artifacts unless you run cleanup first.",
    ]


def _assess_ultrawork_resume_preflight_state() -> tuple[UltraworkStateClassification, list[str]]:
    """Handles assess ultrawork resume preflight state.
    
    Returns:
        tuple[UltraworkStateClassification, list[str]]: Function return value.
    """
    existing_state_paths: list[Path] = list_ultrawork_state_paths()
    if not existing_state_paths:
        return UltraworkStateClassification.MISSING, ["No Ultrawork state files found."]

    ultrawork_state_path = get_ultrawork_state_root() / "ultrawork-state.json"
    if not ultrawork_state_path.exists():
        joined_paths: str = ", ".join(str(path) for path in existing_state_paths)
        return UltraworkStateClassification.INVALID, [
            "Ultrawork state exists without a canonical ultrawork-state.json.",
            f"Known Ultrawork files: {joined_paths}",
            "Run cleanup-stale and re-run launch if this is stale recovery.",
        ]

    state_store = json_file_stores.for_path(ultrawork_state_path)
    state_payload: dict[str, object] | None = state_store.read_object()
    if state_payload is None:
        return UltraworkStateClassification.INVALID, [
            "Ultrawork state file is present but unreadable.",
            f"Path: {ultrawork_state_path}",
        ]

    state_class: UltraworkStateClassification = _classify_ultrawork_state_snapshot(state_payload)
    if state_class != UltraworkStateClassification.RESUMABLE:
        return state_class, [
            f"Ultrawork state file class is '{state_class}'.",
            "Resume requires an active or non-terminal Ultrawork state.",
        ]

    warnings: list[str] = ["Ultrawork state classified as resumable."]
    ultrawork_progress_path = get_ultrawork_state_root() / "ultrawork-progress.json"
    if not ultrawork_progress_path.exists():
        warnings.append(
            "Ultrawork progress artifact is missing; resume may lose progress history."
        )

    return UltraworkStateClassification.RESUMABLE, warnings


def _detect_tty_tmux_gate(allow_non_tty: bool) -> list[str]:
    """Handles detect tty tmux gate.
    
    Args:
        allow_non_tty [bool]: Function argument.
    
    Returns:
        list[str]: Function return value.
    """
    warnings: list[str] = []
    if which("tmux") is None:
        warnings.append(
            "tmux was not detected. Ultrawork runs in direct mode without detached tmux HUD. "
            "Install tmux for the normal launch UX."
        )

    if allow_non_tty:
        warnings.append(
            "allow-non-tty is enabled; launch behavior may differ from interactive-tty mode."
        )

    return warnings


def get_ultrawork_state_root(workspace_root: Path | None = None) -> Path:
    """Return the OMX state directory for the current workspace.
    
    Args:
        workspace_root [Path | None]: Function argument.
    
    Returns:
        Path: Function return value.
    """
    resolved_workspace_root: Path
    if workspace_root is None:
        resolved_workspace_root = Path.cwd()
    else:
        resolved_workspace_root = workspace_root

    state_root: Path = resolved_workspace_root / ".omx" / "state"
    return state_root


def list_ultrawork_state_paths(workspace_root: Path | None = None) -> list[Path]:
    """List known Ultrawork state paths that currently exist.
    
    Args:
        workspace_root [Path | None]: Function argument.
    
    Returns:
        list[Path]: Function return value.
    """
    state_root: Path = get_ultrawork_state_root(workspace_root=workspace_root)
    existing_state_paths: list[Path] = []

    relative_name: str
    for relative_name in _ULTRAWORK_STATE_FILENAMES:
        state_path: Path = state_root / relative_name
        if state_path.exists():
            existing_state_paths.append(state_path)

    return existing_state_paths


def require_ultrawork_launch_tty(allow_non_tty: bool) -> None:
    """Validate whether Ultrawork launch may proceed in the current stdin mode.
    
    Args:
        allow_non_tty [bool]: Function argument.
    """
    if allow_non_tty:
        return

    if not sys.stdin.isatty():
        raise ValueError(
            "Ultrawork launch requires an interactive TTY. Retry from a terminal or "
            "pass --allow-non-tty."
        )


def validate_ultrawork_launch_task(task: str) -> str:
    """Normalize and validate task text for Ultrawork launch.
    
    Args:
        task [str]: Function argument.
    
    Returns:
        str: Function return value.
    """
    normalized_task: str = task.strip()
    if normalized_task == "":
        raise ValueError("Task text must not be blank.")

    return normalized_task


def validate_ultrawork_team_prefix(team_size: int, team_role: str) -> str:
    """Normalize and validate one ultrawork `N:role` prefix.
    
    Args:
        team_size [int]: Function argument.
        team_role [str]: Function argument.
    
    Returns:
        str: Function return value.
    """
    if team_size < 1:
        raise ValueError("Team size must be at least 1.")

    normalized_team_role: str = team_role.strip()
    if normalized_team_role == "":
        raise ValueError("Team role must not be blank.")

    team_prefix: str = f"{team_size}:{normalized_team_role}"
    return team_prefix


def build_ultrawork_launch_plan(
    task: str,
    force_cleanup: bool,
    allow_non_tty: bool,
    team_size: int,
    team_role: str,
) -> tuple[list[str], list[str]]:
    """Build launch command and preflight warnings for Ultrawork.
    
    Args:
        task [str]: Function argument.
        force_cleanup [bool]: Function argument.
        allow_non_tty [bool]: Function argument.
        team_size [int]: Function argument.
        team_role [str]: Function argument.
    
    Returns:
        tuple[list[str], list[str]]: Function return value.
    """
    normalized_task: str = validate_ultrawork_launch_task(task)
    require_ultrawork_launch_tty(allow_non_tty=allow_non_tty)

    warnings: list[str] = []
    warnings.extend(_detect_tty_tmux_gate(allow_non_tty=allow_non_tty))

    state_class, state_warnings = _assess_ultrawork_launch_preflight_state()
    warnings.extend(state_warnings)

    if state_class == "resumable" and not force_cleanup:
        raise ValueError(
            "Existing resumable Ultrawork state detected. "
            "Run `agent-remote ultrawork cleanup-stale` or retry with --force-cleanup."
        )

    team_prefix: str = validate_ultrawork_team_prefix(team_size, team_role)
    launch_command: list[str] = ["team", team_prefix, normalized_task]
    return launch_command, warnings


def build_ultrawork_resume_plan(team_name: str) -> tuple[list[str], list[str]]:
    """Build resume command and preflight warnings for Ultrawork.
    
    Args:
        team_name [str]: Function argument.
    
    Returns:
        tuple[list[str], list[str]]: Function return value.
    """
    normalized_team_name: str = team_name.strip()
    if normalized_team_name == "":
        raise ValueError("Team name must not be blank.")

    state_class, warnings = _assess_ultrawork_resume_preflight_state()
    if state_class != UltraworkStateClassification.RESUMABLE:
        if state_class == UltraworkStateClassification.MISSING:
            raise ValueError(
                "No Ultrawork state found. Launch Ultrawork first or restore a resumable Ultrawork state."
            )
        raise ValueError("No resumable Ultrawork session found.")

    resume_command: list[str] = ["team", "resume", normalized_team_name]
    return resume_command, warnings


def cleanup_ultrawork_state(workspace_root: Path | None = None) -> list[str]:
    """Remove known Ultrawork stale-state files.
    
    Args:
        workspace_root [Path | None]: Function argument.
    
    Returns:
        list[str]: Function return value.
    """
    existing_state_paths: list[Path] = list_ultrawork_state_paths(workspace_root=workspace_root)
    removed_paths: list[str] = []

    state_path: Path
    for state_path in existing_state_paths:
        state_path.unlink()
        removed_paths.append(str(state_path))

    return removed_paths


def format_resume_outcome(
    command_result: OmxCommandResult,
    team_name: str,
) -> OmxCommandResult:
    """Normalize known Ultrawork resume non-resumable responses into a failure envelope.
    
    Args:
        command_result [OmxCommandResult]: Function argument.
        team_name [str]: Function argument.
    
    Returns:
        OmxCommandResult: Function return value.
    """
    normalized_stdout: str = command_result.stdout.strip().lower()
    no_resumable_message: str = (
        f"no resumable team found for {team_name.strip().lower()}"
    )
    if command_result.exit_code == 0 and normalized_stdout == no_resumable_message:
        failure_result = format_preflight_failure(
            "No resumable Ultrawork team found. Launch Ultrawork first or restore a resumable Ultrawork runtime."
        )
        return failure_result

    return command_result


def format_preflight_failure(message: str) -> OmxCommandResult:
    """Return a typed command result for Ultrawork preflight failures.
    
    Args:
        message [str]: Function argument.
    
    Returns:
        OmxCommandResult: Function return value.
    """
    failure_result = OmxCommandResult(exit_code=2, stdout="", stderr=message)
    return failure_result
