from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from omx_remote.execution.codex_invoke import (
    is_codex_goal_session_active,
    spawn_codex_goal_session,
)
from omx_remote.schemas.codex_goal import (
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


def _build_codex_goal_command() -> list[str]:
    codex_command: list[str] = ["codex", "--enable", "goals"]
    return codex_command



def _build_slash_command_text(objective_text: str) -> str:
    normalized_objective_text: str = objective_text.strip()
    slash_command_text: str = f"/goal {normalized_objective_text}"
    return slash_command_text



def _build_goal_handoff_state(
    execution_shape: CodexGoalExecutionShape,
) -> CodexGoalHandoffState:
    if execution_shape == CodexGoalExecutionShape.GOAL_ONLY:
        handoff_state: CodexGoalHandoffState = CodexGoalHandoffState.GOAL_ONLY
        return handoff_state

    handoff_state = CodexGoalHandoffState.AWAITING_RALPH
    return handoff_state



def _build_tracking_state(
    spawn_result: CodexGoalSpawnResult,
) -> CodexGoalTrackingState:
    if spawn_result.spawn_status == CodexGoalSpawnStatus.STARTED:
        tracking_state: CodexGoalTrackingState = CodexGoalTrackingState.STARTING
        return tracking_state

    tracking_state = CodexGoalTrackingState.UNKNOWN
    return tracking_state



def _utcnow_text() -> str:
    launched_at: str = datetime.now(UTC).isoformat()
    return launched_at



def _build_goal_id() -> str:
    goal_id: str = f"goal-{uuid4().hex[:12]}"
    return goal_id



def _resolve_working_directory(working_directory: str | None) -> str:
    if working_directory is None:
        resolved_working_directory: str = str(Path.cwd())
        return resolved_working_directory

    resolved_working_directory = str(Path(working_directory).resolve())
    return resolved_working_directory



def get_codex_goal_state_path(working_directory: str | None = None) -> Path:
    """Return the adapter-owned mirror-state path for native Codex Goal."""
    resolved_working_directory: str = _resolve_working_directory(working_directory)
    state_path: Path = (
        Path(resolved_working_directory) / ".agent-remote" / "state" / "codex-goal.json"
    )
    return state_path



def write_codex_goal_mirror_state(mirror_state: CodexGoalMirrorState) -> None:
    """Persist the latest adapter-owned native Codex Goal mirror state."""
    state_path: Path = get_codex_goal_state_path(mirror_state.working_directory)
    state_store = json_file_stores.for_path(state_path)
    state_store.write_model(mirror_state)



def read_codex_goal_mirror_state(
    working_directory: str | None = None,
) -> CodexGoalMirrorState:
    """Read the latest adapter-owned native Codex Goal mirror state."""
    state_path: Path = get_codex_goal_state_path(working_directory)
    if not state_path.exists():
        raise ValueError(
            "Missing native Codex Goal mirror state at .agent-remote/state/codex-goal.json."
        )

    state_store = json_file_stores.for_path(state_path)
    payload: dict[str, object] | None = state_store.read_object()
    if payload is None:
        raise ValueError(
            "Native Codex Goal mirror state exists but is not a JSON object."
        )

    result: CodexGoalMirrorState = CodexGoalMirrorState.model_validate(payload)
    return result



def start_codex_goal(request: CodexGoalLaunchRequest) -> CodexGoalLaunchResult:
    """Start one adapter-tracked native Codex Goal session."""
    goal_id: str = _build_goal_id()
    resolved_working_directory: str = _resolve_working_directory(request.working_directory)
    codex_command: list[str] = _build_codex_goal_command()
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
        launched_at=_utcnow_text(),
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



def read_codex_goal_status(working_directory: str | None = None) -> CodexGoalMirrorState:
    """Read the latest native Codex Goal mirror state and refresh its tracking state."""
    mirror_state: CodexGoalMirrorState = read_codex_goal_mirror_state(working_directory)
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



def mark_codex_goal_handoff_started(
    *,
    goal_id: str,
    working_directory: str | None = None,
) -> CodexGoalMirrorState:
    """Mark the adapter-owned native Goal mirror state as handed off into Ralph-owned execution."""
    mirror_state: CodexGoalMirrorState = read_codex_goal_mirror_state(working_directory)
    if mirror_state.goal_id != goal_id:
        raise ValueError(
            f"Goal handoff state belongs to {mirror_state.goal_id}, not {goal_id}."
        )

    updated_state: CodexGoalMirrorState = mirror_state.model_copy(
        update={"handoff_state": CodexGoalHandoffState.RALPH_STARTED}
    )
    write_codex_goal_mirror_state(updated_state)
    return updated_state
