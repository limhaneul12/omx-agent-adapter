from __future__ import annotations

from pathlib import Path

from omx_remote.adapter_types.json_types import JsonObject
from omx_remote.execution.codex_invoke import (
    is_codex_goal_session_active,
    spawn_codex_goal_session,
)
from omx_remote.schemas.codex_goal.runtime_schemas import (
    CodexGoalExecutionShape,
    CodexGoalHandoffState,
    CodexGoalLaunchRequest,
    CodexGoalLaunchResult,
    CodexGoalMirrorSource,
    CodexGoalMirrorState,
    CodexGoalSpawnResult,
    CodexGoalSpawnStatus,
    CodexGoalTrackingState,
)
from omx_remote.shared.utils.json_file_store import json_file_stores
from omx_remote.shared.utils.runtime_identity import build_scoped_id, utcnow_text


def _build_codex_goal_command() -> tuple[str, ...]:
    """Handles build codex goal command.

    Returns:
        tuple[str, ...]: Function return value.
    """
    codex_command: tuple[str, ...] = ("codex", "--enable", "goals")
    return codex_command


def _build_slash_command_text(objective_text: str) -> str:
    """Handles build slash command text.

    Args:
        objective_text [str]: Function argument.

    Returns:
        str: Function return value.
    """
    normalized_objective_text: str = objective_text.strip()
    slash_command_text: str = f"/goal {normalized_objective_text}"
    return slash_command_text


def _build_goal_handoff_state(
    execution_shape: CodexGoalExecutionShape,
) -> CodexGoalHandoffState:
    """Handles build goal handoff state.

    Args:
        execution_shape [CodexGoalExecutionShape]: Function argument.

    Returns:
        CodexGoalHandoffState: Function return value.
    """
    if execution_shape == CodexGoalExecutionShape.GOAL_ONLY:
        handoff_state: CodexGoalHandoffState = CodexGoalHandoffState.GOAL_ONLY
        return handoff_state

    handoff_state = CodexGoalHandoffState.AWAITING_RALPH
    return handoff_state


def _build_tracking_state(
    spawn_result: CodexGoalSpawnResult,
) -> CodexGoalTrackingState:
    """Handles build tracking state.

    Args:
        spawn_result [CodexGoalSpawnResult]: Function argument.

    Returns:
        CodexGoalTrackingState: Function return value.
    """
    if spawn_result.spawn_status == CodexGoalSpawnStatus.STARTED:
        tracking_state: CodexGoalTrackingState = CodexGoalTrackingState.STARTING
        return tracking_state

    tracking_state = CodexGoalTrackingState.UNKNOWN
    return tracking_state


def _resolve_working_directory(working_directory: str | None) -> str:
    """Handles resolve working directory.

    Args:
        working_directory [str | None]: Function argument.

    Returns:
        str: Function return value.
    """
    if working_directory is None:
        resolved_working_directory: str = str(Path.cwd())
        return resolved_working_directory

    resolved_working_directory = str(Path(working_directory).resolve())
    return resolved_working_directory


class CodexGoalMirrorStateStore:
    """Owns persistence for adapter-tracked native Codex Goal mirror state."""

    def __init__(self, working_directory: str | None = None) -> None:
        """Initializes a mirror-state store for one workspace.

        Args:
            working_directory [str | None]: Optional workspace whose `.comx-agent` state should be used.
        """
        resolved_working_directory: str = _resolve_working_directory(working_directory)
        self.working_directory: str = resolved_working_directory
        self.state_path: Path = (
            Path(resolved_working_directory)
            / ".comx-agent"
            / "state"
            / "codex-goal.json"
        )

    def write_mirror_state(self, mirror_state: CodexGoalMirrorState) -> None:
        """Persists one native Codex Goal mirror-state snapshot.

        Args:
            mirror_state [CodexGoalMirrorState]: Adapter-owned mirror state to write.
        """
        state_store = json_file_stores.for_path(self.state_path)
        state_store.write_model(mirror_state)

    def read_mirror_state(self) -> CodexGoalMirrorState:
        """Reads the latest native Codex Goal mirror-state snapshot.

        Returns:
            CodexGoalMirrorState: Latest persisted adapter-owned mirror state.

        Raises:
            ValueError: Raised when the mirror state is missing or not JSON-object shaped.
        """
        if not self.state_path.exists():
            raise ValueError(
                "Missing native Codex Goal mirror state at .comx-agent/state/codex-goal.json."
            )

        state_store = json_file_stores.for_path(self.state_path)
        payload: JsonObject | None = state_store.read_object()
        if payload is None:
            raise ValueError(
                "Native Codex Goal mirror state exists but is not a JSON object."
            )

        result: CodexGoalMirrorState = CodexGoalMirrorState.model_validate(payload)
        return result

    def read_status(self) -> CodexGoalMirrorState:
        """Reads mirror state and refreshes its live tmux tracking status.

        Returns:
            CodexGoalMirrorState: Mirror state with refreshed tracking status.
        """
        mirror_state: CodexGoalMirrorState = self.read_mirror_state()
        is_active: bool = is_codex_goal_session_active(mirror_state.session_locator)
        tracking_state: CodexGoalTrackingState
        if is_active:
            tracking_state = CodexGoalTrackingState.ACTIVE
        else:
            tracking_state = CodexGoalTrackingState.ENDED

        refreshed_state: CodexGoalMirrorState = mirror_state.model_copy(
            update={"tracking_state": tracking_state}
        )
        return refreshed_state

    def mark_handoff_started(self, goal_id: str) -> CodexGoalMirrorState:
        """Marks the persisted Goal mirror state as handed off into Ralph execution.

        Args:
            goal_id [str]: Goal identifier expected to own the mirror state.

        Returns:
            CodexGoalMirrorState: Updated and persisted mirror state.

        Raises:
            ValueError: Raised when the persisted mirror state belongs to another Goal.
        """
        mirror_state: CodexGoalMirrorState = self.read_mirror_state()
        if mirror_state.goal_id != goal_id:
            raise ValueError(
                f"Goal handoff state belongs to {mirror_state.goal_id}, not {goal_id}."
            )

        updated_state: CodexGoalMirrorState = mirror_state.model_copy(
            update={"handoff_state": CodexGoalHandoffState.RALPH_STARTED}
        )
        self.write_mirror_state(updated_state)
        return updated_state


def get_codex_goal_state_path(working_directory: str | None = None) -> Path:
    """Return the adapter-owned mirror-state path for native Codex Goal.

    Args:
        working_directory [str | None]: Function argument.

    Returns:
        Path: Function return value.
    """
    resolved_working_directory: str = _resolve_working_directory(working_directory)
    store = CodexGoalMirrorStateStore(resolved_working_directory)
    state_path: Path = store.state_path
    return state_path


def write_codex_goal_mirror_state(mirror_state: CodexGoalMirrorState) -> None:
    """Persist the latest adapter-owned native Codex Goal mirror state.

    Args:
        mirror_state [CodexGoalMirrorState]: Function argument.
    """
    store = CodexGoalMirrorStateStore(mirror_state.working_directory)
    store.write_mirror_state(mirror_state)


def read_codex_goal_mirror_state(
    working_directory: str | None = None,
) -> CodexGoalMirrorState:
    """Read the latest adapter-owned native Codex Goal mirror state.

    Args:
        working_directory [str | None]: Function argument.

    Returns:
        CodexGoalMirrorState: Function return value.
    """
    store = CodexGoalMirrorStateStore(working_directory)
    result: CodexGoalMirrorState = store.read_mirror_state()
    return result


def start_codex_goal(request: CodexGoalLaunchRequest) -> CodexGoalLaunchResult:
    """Start one adapter-tracked native Codex Goal session.

    Args:
        request [CodexGoalLaunchRequest]: Function argument.

    Returns:
        CodexGoalLaunchResult: Function return value.
    """
    goal_id: str = build_scoped_id("goal")
    resolved_working_directory: str = _resolve_working_directory(
        request.working_directory
    )
    codex_command: tuple[str, ...] = _build_codex_goal_command()
    slash_command_text: str = _build_slash_command_text(request.objective_text)
    spawn_result: CodexGoalSpawnResult = spawn_codex_goal_session(
        goal_id=goal_id,
        codex_command=codex_command,
        working_directory=resolved_working_directory,
        slash_command_text=slash_command_text,
    )
    mirror_state: CodexGoalMirrorState = CodexGoalMirrorState(
        goal_id=goal_id,
        objective_text=request.objective_text.strip(),
        source=CodexGoalMirrorSource.CODEX_GOAL,
        execution_shape=request.execution_shape,
        review_policy=request.review_policy,
        team_worker_count=request.team_worker_count,
        working_directory=resolved_working_directory,
        codex_command=codex_command,
        session_locator=spawn_result.session_locator,
        process_id=spawn_result.process_id,
        launched_at=utcnow_text(),
        handoff_state=_build_goal_handoff_state(request.execution_shape),
        tracking_state=_build_tracking_state(spawn_result),
    )
    write_codex_goal_mirror_state(mirror_state)

    warnings: list[str] = []
    if not spawn_result.slash_command_written:
        warnings.append(
            "native Codex Goal session started, but the wrapper could not inject the initial /goal command"
        )

    result: CodexGoalLaunchResult = CodexGoalLaunchResult(
        mirror_state=mirror_state,
        spawn_result=spawn_result,
        slash_command_injected=spawn_result.slash_command_written,
        warnings=warnings,
    )
    return result


def read_codex_goal_status(
    working_directory: str | None = None,
) -> CodexGoalMirrorState:
    """Read the latest native Codex Goal mirror state and refresh its tracking state.

    Args:
        working_directory [str | None]: Function argument.

    Returns:
        CodexGoalMirrorState: Function return value.
    """
    store = CodexGoalMirrorStateStore(working_directory)
    refreshed_state: CodexGoalMirrorState = store.read_status()
    return refreshed_state


def mark_codex_goal_handoff_started(
    goal_id: str,
    working_directory: str | None = None,
) -> CodexGoalMirrorState:
    """Mark the adapter-owned native Goal mirror state as handed off into Ralph-owned execution.

    Args:
        goal_id [str]: Function argument.
        working_directory [str | None]: Function argument.

    Returns:
        CodexGoalMirrorState: Function return value.
    """
    store = CodexGoalMirrorStateStore(working_directory)
    updated_state: CodexGoalMirrorState = store.mark_handoff_started(goal_id)
    return updated_state
