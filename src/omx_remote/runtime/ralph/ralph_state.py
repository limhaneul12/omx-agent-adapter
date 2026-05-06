import sys
from pathlib import Path
from shutil import which

from omx_remote.adapter_types.type_contract.ralph_contract_type import (
    RALPH_NON_TERMINAL_OUTCOMES,
    RALPH_NON_TERMINAL_PHASES,
    RALPH_TERMINAL_OUTCOMES,
    RALPH_TERMINAL_PHASES,
)
from omx_remote.shared.omx_enums.ralph_enums import (
    RalphRunOutcome,
    RalphRuntimePhase,
    RalphStateClassification,
)
from omx_remote.shared.utils.json_file_store import json_file_stores

_RALPH_STATE_FILENAMES: tuple[str, ...] = (
    "ralph-state.json",
    "ralph-progress.json",
    "run-state.json",
)


def normalize_ralph_state_token(value: object) -> str | None:
    """Normalizes one raw Ralph state marker token.

    Args:
        value [object]: Raw value loaded from a Ralph state artifact.

    Returns:
        str | None: Lowercase non-blank token, or `None` when unavailable.
    """
    if not isinstance(value, str):
        return None

    token: str = value.strip().lower()
    return token or None


def read_json_object(path: Path) -> dict[str, object] | None:
    """Reads one JSON object from an adapter-owned file store.

    Args:
        path [Path]: JSON file path to read.

    Returns:
        dict[str, object] | None: Parsed object, or `None` when missing/unreadable/non-object.
    """
    state_store = json_file_stores.for_path(path)
    object_payload: dict[str, object] | None = state_store.read_object()
    return object_payload


class RalphStateClassifier:
    """Classifies adapter-visible Ralph runtime state markers."""

    @staticmethod
    def normalize_phase(phase_value: object) -> RalphRuntimePhase | None:
        """Normalizes a raw Ralph phase marker.

        Args:
            phase_value [object]: Raw phase value loaded from state.

        Returns:
            RalphRuntimePhase | None: Parsed phase enum, or `None` for missing/unknown values.
        """
        normalized_phase: str | None = normalize_ralph_state_token(phase_value)
        if normalized_phase is None:
            return None

        try:
            parsed_phase: RalphRuntimePhase = RalphRuntimePhase(normalized_phase)
        except ValueError:
            return None

        return parsed_phase

    @staticmethod
    def normalize_outcome(outcome_value: object) -> RalphRunOutcome | None:
        """Normalizes a raw Ralph outcome marker.

        Args:
            outcome_value [object]: Raw outcome value loaded from state.

        Returns:
            RalphRunOutcome | None: Parsed outcome enum, or `None` for missing/unknown values.
        """
        normalized_outcome: str | None = normalize_ralph_state_token(outcome_value)
        if normalized_outcome is None:
            return None

        try:
            parsed_outcome: RalphRunOutcome = RalphRunOutcome(normalized_outcome)
        except ValueError:
            return None

        return parsed_outcome

    @classmethod
    def is_terminal_phase(cls, phase_value: object) -> bool:
        """Checks whether a raw phase marker is terminal.

        Args:
            phase_value [object]: Raw phase value loaded from state.

        Returns:
            bool: `True` when the phase is a terminal Ralph phase.
        """
        phase: RalphRuntimePhase | None = cls.normalize_phase(phase_value)
        terminal_phase: bool = phase in RALPH_TERMINAL_PHASES
        return terminal_phase

    @classmethod
    def is_terminal_outcome(cls, outcome_value: object) -> bool:
        """Checks whether a raw outcome marker is terminal.

        Args:
            outcome_value [object]: Raw outcome value loaded from state.

        Returns:
            bool: `True` when the outcome is a terminal Ralph outcome.
        """
        outcome: RalphRunOutcome | None = cls.normalize_outcome(outcome_value)
        terminal_outcome: bool = outcome in RALPH_TERMINAL_OUTCOMES
        return terminal_outcome

    @classmethod
    def is_active_phase(cls, phase_value: object) -> bool:
        """Checks whether a raw phase marker is active/resumable.

        Args:
            phase_value [object]: Raw phase value loaded from state.

        Returns:
            bool: `True` when the phase is a non-terminal Ralph phase.
        """
        phase: RalphRuntimePhase | None = cls.normalize_phase(phase_value)
        active_phase: bool = phase in RALPH_NON_TERMINAL_PHASES
        return active_phase

    @classmethod
    def is_active_outcome(cls, outcome_value: object) -> bool:
        """Checks whether a raw outcome marker is active/resumable.

        Args:
            outcome_value [object]: Raw outcome value loaded from state.

        Returns:
            bool: `True` when the outcome is a non-terminal Ralph outcome.
        """
        outcome: RalphRunOutcome | None = cls.normalize_outcome(outcome_value)
        active_outcome: bool = outcome in RALPH_NON_TERMINAL_OUTCOMES
        return active_outcome

    @classmethod
    def classify_state_snapshot(
        cls,
        state_payload: dict[str, object],
    ) -> RalphStateClassification:
        """Classifies a Ralph state artifact as resumable, terminal, or stale.

        Args:
            state_payload [dict[str, object]]: Raw state payload loaded from `.omx/state`.

        Returns:
            RalphStateClassification: Adapter-visible Ralph state classification.
        """
        active_value: object | None = state_payload.get("active")

        if active_value is True:
            return RalphStateClassification.RESUMABLE
        if active_value is False:
            return cls._classify_inactive_state(state_payload)
        if active_value is not None and not isinstance(active_value, bool):
            return RalphStateClassification.STALE

        unknown_active_state: RalphStateClassification = cls._classify_marker_state(
            state_payload
        )
        return unknown_active_state

    @classmethod
    def _classify_inactive_state(
        cls,
        state_payload: dict[str, object],
    ) -> RalphStateClassification:
        """Classifies an explicitly inactive Ralph state payload.

        Args:
            state_payload [dict[str, object]]: Raw state payload with `active=false`.

        Returns:
            RalphStateClassification: Terminal, resumable, or stale classification.
        """
        outcome_value: object | None = cls._read_outcome_value(state_payload)
        phase_value: object | None = state_payload.get("current_phase")

        if cls.is_terminal_outcome(outcome_value) or cls.is_terminal_phase(phase_value):
            return RalphStateClassification.TERMINAL
        if cls.is_active_outcome(outcome_value) or cls.is_active_phase(phase_value):
            return RalphStateClassification.RESUMABLE

        return RalphStateClassification.STALE

    @classmethod
    def _classify_marker_state(
        cls,
        state_payload: dict[str, object],
    ) -> RalphStateClassification:
        """Classifies a Ralph state payload using phase/outcome markers only.

        Args:
            state_payload [dict[str, object]]: Raw state payload without a boolean `active` marker.

        Returns:
            RalphStateClassification: Terminal, resumable, or stale classification.
        """
        outcome_value: object | None = cls._read_outcome_value(state_payload)
        phase_value: object | None = state_payload.get("current_phase")

        if cls.is_terminal_outcome(outcome_value):
            return RalphStateClassification.TERMINAL
        if cls.is_active_outcome(outcome_value) or cls.is_active_phase(phase_value):
            return RalphStateClassification.RESUMABLE
        if cls.is_terminal_phase(phase_value):
            return RalphStateClassification.TERMINAL

        return RalphStateClassification.STALE

    @staticmethod
    def _read_outcome_value(state_payload: dict[str, object]) -> object | None:
        """Reads the supported Ralph outcome marker from state payloads.

        Args:
            state_payload [dict[str, object]]: Raw state payload.

        Returns:
            object | None: Raw `run_outcome` or fallback `outcome` value.
        """
        outcome_value: object | None = state_payload.get("run_outcome")
        if outcome_value is None:
            outcome_value = state_payload.get("outcome")

        return outcome_value


def classify_ralph_state_snapshot(
    state_payload: dict[str, object],
) -> RalphStateClassification:
    """Classifies Ralph state as resumable, terminal, or stale.

    Args:
        state_payload [dict[str, object]]: Raw state payload loaded from `.omx/state`.

    Returns:
        RalphStateClassification: Adapter-visible Ralph state classification.
    """
    state_classification: RalphStateClassification = (
        RalphStateClassifier.classify_state_snapshot(state_payload)
    )
    return state_classification


def get_ralph_state_root(workspace_root: Path | None = None) -> Path:
    """Returns the OMX state directory for the current workspace.

    Args:
        workspace_root [Path | None]: Optional explicit workspace root.

    Returns:
        Path: The `.omx/state` directory path for the workspace.
    """
    resolved_workspace_root: Path = Path.cwd() if workspace_root is None else workspace_root
    state_root: Path = resolved_workspace_root / ".omx" / "state"
    return state_root


def list_ralph_state_paths(workspace_root: Path | None = None) -> list[Path]:
    """Lists known Ralph state paths that currently exist.

    Args:
        workspace_root [Path | None]: Optional explicit workspace root.

    Returns:
        list[Path]: Existing known Ralph state files.
    """
    state_root: Path = get_ralph_state_root(workspace_root=workspace_root)
    existing_state_paths: list[Path] = []

    for relative_name in _RALPH_STATE_FILENAMES:
        state_path: Path = state_root / relative_name
        if state_path.exists():
            existing_state_paths.append(state_path)

    return existing_state_paths


def assess_ralph_launch_preflight_state() -> tuple[RalphStateClassification, list[str]]:
    """Assesses whether Ralph launch can proceed with existing state artifacts.

    Returns:
        tuple[RalphStateClassification, list[str]]: State classification plus preflight warnings.
    """
    existing_state_paths: list[Path] = list_ralph_state_paths()
    if not existing_state_paths:
        return RalphStateClassification.CLEAN, []

    ralph_state_path: Path = get_ralph_state_root() / "ralph-state.json"
    joined_paths: str = ", ".join(str(path) for path in existing_state_paths)
    if ralph_state_path not in existing_state_paths:
        return RalphStateClassification.STALE, [
            "Existing Ralph state files were found, but no ralph-state.json was present.",
            f"Known stale files: {joined_paths}",
            "If these are stale, run `agent-remote ralph cleanup-stale` before re-launching.",
        ]

    ralph_state_payload: dict[str, object] | None = read_json_object(ralph_state_path)
    if ralph_state_payload is None:
        return RalphStateClassification.TERMINAL, [
            "Ralph state artifact is present but unreadable.",
            f"Paths: {joined_paths}",
            "Clean stale Ralph artifacts and retry with `agent-remote ralph cleanup-stale`.",
        ]

    state_class: RalphStateClassification = classify_ralph_state_snapshot(ralph_state_payload)
    if state_class == RalphStateClassification.RESUMABLE:
        return RalphStateClassification.RESUMABLE, [
            "Ralph appears resumable from existing state.",
            f"Paths: {joined_paths}",
            "If you intend to start a new session, run `agent-remote ralph cleanup-stale` or use --force-cleanup.",
        ]
    if state_class == RalphStateClassification.TERMINAL:
        return RalphStateClassification.TERMINAL, [
            "Ralph state exists and is terminal/non-runnable.",
            f"Paths: {joined_paths}",
            "Proceeding is treated as a stale-state recovery path.",
        ]

    return RalphStateClassification.STALE, [
        "Ralph state exists but lacks explicit resumability markers.",
        f"Paths: {joined_paths}",
        "Proceeding may overwrite stale artifacts unless you run cleanup first.",
    ]


def assess_ralph_resume_preflight_state() -> tuple[RalphStateClassification, list[str]]:
    """Assesses whether Ralph resume can proceed with existing state artifacts.

    Returns:
        tuple[RalphStateClassification, list[str]]: State classification plus resumability warnings.
    """
    existing_state_paths: list[Path] = list_ralph_state_paths()
    if not existing_state_paths:
        return RalphStateClassification.MISSING, ["No Ralph state files found."]

    ralph_state_path = get_ralph_state_root() / "ralph-state.json"
    if not ralph_state_path.exists():
        joined_paths: str = ", ".join(str(path) for path in existing_state_paths)
        return RalphStateClassification.INVALID, [
            "Ralph state exists without a canonical ralph-state.json.",
            f"Known Ralph files: {joined_paths}",
            "Run cleanup-stale and re-run launch if this is stale recovery.",
        ]

    state_payload: dict[str, object] | None = read_json_object(ralph_state_path)
    if state_payload is None:
        return RalphStateClassification.INVALID, [
            "Ralph state file is present but unreadable.",
            f"Path: {ralph_state_path}",
        ]

    state_class: RalphStateClassification = classify_ralph_state_snapshot(state_payload)
    if state_class != RalphStateClassification.RESUMABLE:
        return state_class, [
            f"Ralph state file class is '{state_class}'.",
            "Resume requires an active or non-terminal Ralph state.",
        ]

    warnings: list[str] = ["Ralph state classified as resumable."]
    ralph_progress_path = get_ralph_state_root() / "ralph-progress.json"
    if not ralph_progress_path.exists():
        warnings.append("Ralph progress artifact is missing; resume may lose progress history.")

    return RalphStateClassification.RESUMABLE, warnings


def detect_tty_tmux_gate(allow_non_tty: bool, operator_name: str) -> list[str]:
    """Detects common TTY/tmux warnings for operator launch commands.

    Args:
        allow_non_tty [bool]: Whether non-interactive launch is explicitly allowed.
        operator_name [str]: Human-readable operator name for warning text.

    Returns:
        list[str]: Non-blocking launch environment warnings.
    """
    warnings: list[str] = []
    if which("tmux") is None:
        warnings.append(
            f"tmux was not detected. {operator_name} runs in direct mode without detached tmux HUD. "
            "Install tmux for the normal launch UX."
        )
    if allow_non_tty:
        warnings.append(
            "allow-non-tty is enabled; launch behavior may differ from interactive-tty mode."
        )

    return warnings


def require_ralph_launch_tty(allow_non_tty: bool) -> None:
    """Validates whether Ralph launch may proceed in the current stdin mode.

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


def cleanup_ralph_state(workspace_root: Path | None = None) -> list[str]:
    """Removes known Ralph stale-state files.

    Args:
        workspace_root [Path | None]: Optional explicit workspace root.

    Returns:
        list[str]: Removed file paths as strings.
    """
    existing_state_paths: list[Path] = list_ralph_state_paths(workspace_root=workspace_root)
    removed_paths: list[str] = []

    for state_path in existing_state_paths:
        state_path.unlink()
        removed_paths.append(str(state_path))

    return removed_paths
