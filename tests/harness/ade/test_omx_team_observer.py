from __future__ import annotations

import shutil
from pathlib import Path

import orjson
import pytest
from comx_harness.ade.omx_team_discovery import discover_omx_team_names
from comx_harness.ade.omx_team_native import NativeCommandResult, OmxTeamObserver
from comx_harness.ade.omx_team_projection import build_omx_attach_argv
from comx_harness.schemas.lifecycle_schemas import EventReport, RunEvent
from comx_harness.shared.harness_enums.lifecycle_enums import EventKind
from comx_harness.shared.harness_enums.operator_enums import AgentStatus


def _result(payload: object) -> NativeCommandResult:
    return NativeCommandResult(
        return_code=0,
        stdout=orjson.dumps(payload).decode("utf-8") + "\n",
        stderr="",
    )


def _runner(argv: tuple[str, ...], cwd: Path) -> NativeCommandResult:
    assert cwd.is_absolute()
    if argv[2] == "status":
        return _result(
            {
                "schema_version": "1.0",
                "command": "omx team status",
                "team_name": "alpha-team",
                "status": "running",
            }
        )
    operation = argv[3]
    if operation == "read-config":
        return _result(
            {
                "ok": True,
                "operation": operation,
                "data": {
                    "config": {
                        "name": "alpha-team",
                        "task": "Fix tests",
                        "worker_count": 2,
                        "tmux_session": "omx-team-alpha-team",
                        "leader_pane_id": "%1",
                        "workspace_mode": "worktree",
                        "workers": [
                            {
                                "name": "worker-1",
                                "index": 1,
                                "role": "executor",
                                "assigned_tasks": ["1"],
                                "pane_id": "%2",
                                "worktree_path": "/tmp/alpha-1",
                                "worktree_branch": "team/alpha-1",
                            },
                            {
                                "name": "worker-2",
                                "index": 2,
                                "role": "reviewer",
                                "assigned_tasks": ["2"],
                                "pane_id": "%3",
                            },
                        ],
                    }
                },
            }
        )
    if operation == "list-tasks":
        return _result(
            {
                "ok": True,
                "operation": operation,
                "data": {
                    "count": 2,
                    "tasks": [
                        {
                            "id": "1",
                            "subject": "Implement",
                            "status": "in_progress",
                            "owner": "worker-1",
                        },
                        {
                            "id": "2",
                            "subject": "Review",
                            "status": "blocked",
                            "owner": "worker-2",
                            "blocked_by": ["1"],
                        },
                    ],
                },
            }
        )
    if operation == "get-summary":
        return _result(
            {
                "ok": True,
                "operation": operation,
                "data": {
                    "summary": {
                        "teamName": "alpha-team",
                        "workerCount": 2,
                        "tasks": {"total": 2, "blocked": 1, "in_progress": 1},
                        "workers": [
                            {
                                "name": "worker-1",
                                "alive": True,
                                "lastTurnAt": "2026-07-28T00:00:00Z",
                                "turnsWithoutProgress": 0,
                            },
                            {
                                "name": "worker-2",
                                "alive": False,
                                "lastTurnAt": None,
                                "turnsWithoutProgress": 3,
                            },
                        ],
                        "nonReportingWorkers": ["worker-2"],
                    }
                },
            }
        )
    assert operation == "read-monitor-snapshot"
    return _result(
        {
            "ok": True,
            "operation": operation,
            "data": {
                "snapshot": {
                    "workerAliveByName": {"worker-1": True, "worker-2": False},
                    "workerStateByName": {
                        "worker-1": "working",
                        "worker-2": "blocked",
                    },
                    "workerTurnCountByName": {"worker-1": 4, "worker-2": 1},
                    "workerTaskIdByName": {"worker-1": "1", "worker-2": "2"},
                    "taskStatusById": {"1": "in_progress", "2": "blocked"},
                }
            },
        }
    )


def test_discovery_reads_message_and_provider_payload() -> None:
    events = EventReport(
        run_id="run-1",
        events=(
            RunEvent(
                run_id="run-1",
                sequence=1,
                timestamp="2026-07-28T00:00:00Z",
                kind=EventKind.PROVIDER,
                message="omx team status alpha-team",
                provider_payload_json='{"team_name":"beta-team"}',
            ),
        ),
    )

    assert discover_omx_team_names(events) == ("alpha-team", "beta-team")


def test_observer_projects_workers_tasks_and_attention(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(shutil, "which", lambda _: "/opt/homebrew/bin/omx")
    team = OmxTeamObserver(tmp_path, runner=_runner).read("alpha-team")

    assert team.available is True
    assert team.tmux_session == "omx-team-alpha-team"
    assert team.workers[0].state == AgentStatus.WORKING
    assert team.workers[0].current_task_id == "1"
    assert team.workers[1].state == AgentStatus.BLOCKED
    assert team.tasks[1].status == "blocked"
    assert any("worker-2" in message for message in team.attention)
    assert any("task 2" in message for message in team.attention)


def test_attach_argv_targets_selected_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(shutil, "which", lambda _: "/opt/homebrew/bin/omx")
    team = OmxTeamObserver(tmp_path, runner=_runner).read("alpha-team")

    assert build_omx_attach_argv(
        team,
        worker_name="worker-2",
        inside_tmux=False,
    ) == (
        "tmux",
        "attach-session",
        "-t",
        "omx-team-alpha-team",
        ";",
        "select-pane",
        "-t",
        "%3",
    )


def test_missing_team_is_reported_without_fabricated_workers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(shutil, "which", lambda _: "/opt/homebrew/bin/omx")

    def missing_runner(argv: tuple[str, ...], cwd: Path) -> NativeCommandResult:
        assert argv[2] == "status"
        assert cwd.is_absolute()
        return _result(
            {
                "team_name": "missing-team",
                "status": "missing",
            }
        )

    team = OmxTeamObserver(tmp_path, runner=missing_runner).read("missing-team")

    assert team.available is False
    assert team.workers == ()
    assert "missing" in team.detail


def test_observer_uses_only_read_only_native_operations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(shutil, "which", lambda _: "/opt/homebrew/bin/omx")
    calls: list[tuple[str, ...]] = []

    def recording_runner(
        argv: tuple[str, ...],
        cwd: Path,
    ) -> NativeCommandResult:
        calls.append(argv)
        return _runner(argv, cwd)

    OmxTeamObserver(tmp_path, runner=recording_runner).read("alpha-team")

    assert calls[0][:3] == ("omx", "team", "status")
    assert {argv[3] for argv in calls[1:]} == {
        "read-config",
        "list-tasks",
        "get-summary",
        "read-monitor-snapshot",
    }
    forbidden = {"start", "shutdown", "update-task", "claim-task", "send-message"}
    assert not any(forbidden.intersection(argv) for argv in calls)
