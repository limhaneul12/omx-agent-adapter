from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from omx_remote.runtime.codex_goal_runtime import (
    mark_codex_goal_handoff_started,
    read_codex_goal_status,
    start_codex_goal,
)
from omx_remote.schemas.codex_goal import (
    CodexGoalLaunchRequest,
    CodexGoalMirrorState,
    CodexGoalSpawnResult,
)


def test_codex_goal_launch_request_rejects_blank_objective_text() -> None:
    with pytest.raises(ValidationError):
        CodexGoalLaunchRequest(objective_text="")



def test_codex_goal_mirror_state_accepts_goal_only_shape() -> None:
    result = CodexGoalMirrorState(
        goal_id="goal-1",
        objective_text="Ship the first native goal bridge",
        source="codex_goal",
        execution_shape="goal_only",
        review_policy="continue_automatically",
        team_worker_count=None,
        working_directory="/tmp/project",
        codex_command=["codex", "--enable", "goals"],
        session_locator="agent-remote-goal-goal-1",
        process_id=1234,
        launched_at="2026-05-05T12:00:00+00:00",
        handoff_state="goal_only",
        tracking_state="starting",
    )

    assert result.execution_shape == "goal_only"
    assert result.handoff_state == "goal_only"



def test_start_codex_goal_builds_goal_enabled_codex_command(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    observed_payload: dict[str, object] = {}

    def fake_spawn_codex_goal_session(
        *,
        goal_id: str,
        codex_command: list[str],
        working_directory: str | None,
        slash_command_text: str,
    ) -> CodexGoalSpawnResult:
        observed_payload["goal_id"] = goal_id
        observed_payload["codex_command"] = codex_command
        observed_payload["working_directory"] = working_directory
        observed_payload["slash_command_text"] = slash_command_text
        result = CodexGoalSpawnResult(
            session_locator=f"agent-remote-goal-{goal_id}",
            process_id=4321,
            spawn_status="started",
            slash_command_written=True,
            error_text=None,
        )
        return result

    monkeypatch.setattr(
        "omx_remote.runtime.codex_goal_runtime.spawn_codex_goal_session",
        fake_spawn_codex_goal_session,
    )

    request = CodexGoalLaunchRequest(
        objective_text="Ship the first native goal bridge",
        execution_shape="ralph_pipeline",
        review_policy="review_required",
        team_worker_count=3,
        working_directory=str(tmp_path),
    )

    result = start_codex_goal(request)

    assert observed_payload["codex_command"] == ["codex", "--enable", "goals"]
    assert observed_payload["working_directory"] == str(tmp_path)
    assert observed_payload["slash_command_text"] == "/goal Ship the first native goal bridge"
    assert result.mirror_state.execution_shape == "ralph_pipeline"
    assert result.mirror_state.team_worker_count == 3



def test_start_codex_goal_records_adapter_owned_mirror_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_spawn_codex_goal_session(
        *,
        goal_id: str,
        codex_command: list[str],
        working_directory: str | None,
        slash_command_text: str,
    ) -> CodexGoalSpawnResult:
        _ = codex_command
        _ = working_directory
        _ = slash_command_text
        result = CodexGoalSpawnResult(
            session_locator=f"agent-remote-goal-{goal_id}",
            process_id=9876,
            spawn_status="started",
            slash_command_written=True,
            error_text=None,
        )
        return result

    monkeypatch.setattr(
        "omx_remote.runtime.codex_goal_runtime.spawn_codex_goal_session",
        fake_spawn_codex_goal_session,
    )

    request = CodexGoalLaunchRequest(
        objective_text="Track native goal startup",
        execution_shape="goal_only",
        review_policy="continue_automatically",
        working_directory=str(tmp_path),
    )

    result = start_codex_goal(request)
    state_path = tmp_path / ".agent-remote" / "state" / "codex-goal.json"

    assert state_path.exists()
    persisted_payload = json.loads(state_path.read_text(encoding="utf-8"))
    assert persisted_payload["goal_id"] == result.mirror_state.goal_id
    assert persisted_payload["objective_text"] == "Track native goal startup"
    assert persisted_payload["source"] == "codex_goal"



def test_read_codex_goal_status_returns_latest_mirror_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    state_dir = tmp_path / ".agent-remote" / "state"
    state_dir.mkdir(parents=True)
    state_path = state_dir / "codex-goal.json"
    state_path.write_text(
        json.dumps(
            {
                "goal_id": "goal-1",
                "objective_text": "Track native goal startup",
                "source": "codex_goal",
                "execution_shape": "ralph_pipeline",
                "review_policy": "review_required",
                "team_worker_count": 2,
                "working_directory": str(tmp_path),
                "codex_command": ["codex", "--enable", "goals"],
                "session_locator": "agent-remote-goal-goal-1",
                "process_id": 1234,
                "launched_at": "2026-05-05T12:00:00+00:00",
                "handoff_state": "awaiting_ralph",
                "tracking_state": "starting"
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "omx_remote.runtime.codex_goal_runtime.is_codex_goal_session_active",
        lambda session_locator: True,
    )

    result = read_codex_goal_status(working_directory=str(tmp_path))

    assert result.goal_id == "goal-1"
    assert result.tracking_state == "active"
    assert result.handoff_state == "awaiting_ralph"



def test_start_codex_goal_marks_slash_command_injected_when_goal_command_is_written(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_spawn_codex_goal_session(
        *,
        goal_id: str,
        codex_command: list[str],
        working_directory: str | None,
        slash_command_text: str,
    ) -> CodexGoalSpawnResult:
        _ = goal_id
        _ = codex_command
        _ = working_directory
        _ = slash_command_text
        result = CodexGoalSpawnResult(
            session_locator="agent-remote-goal-goal-1",
            process_id=2222,
            spawn_status="started",
            slash_command_written=True,
            error_text=None,
        )
        return result

    monkeypatch.setattr(
        "omx_remote.runtime.codex_goal_runtime.spawn_codex_goal_session",
        fake_spawn_codex_goal_session,
    )

    request = CodexGoalLaunchRequest(
        objective_text="Inject native goal command",
        working_directory=str(tmp_path),
    )

    result = start_codex_goal(request)

    assert result.slash_command_injected is True
    assert result.spawn_result.slash_command_written is True



def test_mark_codex_goal_handoff_started_updates_persisted_mirror_state(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / ".agent-remote" / "state"
    state_dir.mkdir(parents=True)
    state_path = state_dir / "codex-goal.json"
    state_path.write_text(
        json.dumps(
            {
                "goal_id": "goal-1",
                "objective_text": "Dispatch native goal into Ralph",
                "source": "codex_goal",
                "execution_shape": "ralph_pipeline",
                "review_policy": "continue_automatically",
                "team_worker_count": None,
                "working_directory": str(tmp_path),
                "codex_command": ["codex", "--enable", "goals"],
                "session_locator": "agent-remote-goal-goal-1",
                "process_id": 1234,
                "launched_at": "2026-05-05T12:00:00+00:00",
                "handoff_state": "awaiting_ralph",
                "tracking_state": "active"
            }
        ),
        encoding="utf-8",
    )

    result = mark_codex_goal_handoff_started(
        goal_id="goal-1",
        working_directory=str(tmp_path),
    )
    persisted_payload = json.loads(state_path.read_text(encoding="utf-8"))

    assert result.handoff_state == "ralph_started"
    assert persisted_payload["handoff_state"] == "ralph_started"
    assert persisted_payload["goal_id"] == "goal-1"
