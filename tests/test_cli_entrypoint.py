import os
import subprocess
from pathlib import Path

import orjson
from typer.testing import CliRunner

from omx_remote.cli import app
from omx_remote.schemas.runtime.status_schemas import (
    RuntimeModeStateSnapshot,
    RuntimeModeStatusResult,
    RuntimeModeStatusSnapshot,
)
from omx_remote.schemas.teamwork.admin_aggregation_schemas import (
    TeamAdminAggregationReport,
)


def _run_agent_remote_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run the agent-remote console entrypoint against local source."""
    env = os.environ.copy()
    repo_root = str(Path(__file__).resolve().parents[1])
    env["PYTHONPATH"] = os.pathsep.join(
        [repo_root, f"{repo_root}/src", os.environ.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)
    command = ["uv", "run", "agent-remote", *args]
    return subprocess.run(
        command,
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def _write_goal_lifecycle_bundle(tmp_path: Path) -> None:
    artifact_dir = tmp_path / ".agent-remote" / "state" / "goal-lifecycle"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "goal_id": "goal-cli",
        "mirror_state": {
            "goal_id": "goal-cli",
            "objective_text": "Restore lifecycle from CLI.",
            "source": "codex_goal",
            "execution_shape": "ralph_pipeline",
            "review_policy": "continue_automatically",
            "team_worker_count": 2,
            "working_directory": str(tmp_path),
            "codex_command": ["codex", "--enable", "goals"],
            "session_locator": "agent-remote-goal-goal-cli",
            "process_id": 1234,
            "launched_at": "2026-05-05T12:00:00+00:00",
            "handoff_state": "ralph_started",
            "tracking_state": "active",
        },
        "aggregation_report": {
            "admin_id": "team-admin",
            "aggregation_state": "ready_for_ralph_review",
            "merge_ready": True,
            "final_report_required": True,
            "completed_workers": ["worker-1", "worker-2"],
            "missing_workers": [],
            "blocked_workers": [],
            "incomplete_workers": [],
            "requires_human_review": False,
            "requires_llm_review": True,
            "task_count": 2,
            "event_count": 2,
            "summary": "Team Admin collected all worker results.",
        },
    }
    (artifact_dir / "goal-cli.json").write_bytes(orjson.dumps(payload))



def _write_codex_goal_mirror_state(tmp_path: Path) -> None:
    artifact_dir = tmp_path / ".agent-remote" / "state"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "goal_id": "goal-cli",
        "objective_text": "Prepare a Ralph handoff from CLI.",
        "source": "codex_goal",
        "execution_shape": "ralph_pipeline",
        "review_policy": "review_required",
        "team_worker_count": 2,
        "working_directory": str(tmp_path),
        "codex_command": ["codex", "--enable", "goals"],
        "session_locator": "agent-remote-goal-goal-cli",
        "process_id": 1234,
        "launched_at": "2026-05-05T12:00:00+00:00",
        "handoff_state": "awaiting_ralph",
        "tracking_state": "active",
    }
    (artifact_dir / "codex-goal.json").write_bytes(orjson.dumps(payload))


def _write_team_admin_prd_artifact(tmp_path: Path) -> Path:
    prd_path = tmp_path / ".omx" / "prd.json"
    prd_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "objective": "Collect Team Admin results from CLI.",
        "scope": ["aggregate Team worker output"],
        "constraints": ["read-only Team API collection"],
        "execution_plan": ["collect tasks/events/statuses"],
        "verification_expectations": ["admin report is valid JSON"],
        "requires_team_fanout": True,
        "team_worker_count": 1,
        "continuation_policy": "review_required",
        "team_worker_assignments": [
            {
                "worker_id": "worker-1",
                "lane_name": "worker-1 lane",
                "objective": "Return one handoff.",
                "owned_files": ["src/worker.py"],
                "read_only_context_files": ["AGENTS.md"],
                "forbidden_files": [".omx/**"],
                "tdd_steps": ["write failing test"],
                "verification_commands": ["uv run pytest -q"],
                "handoff_summary_required": "summarize worker result",
                "authorization_policy": "llm_review",
                "authorization_scope": {
                    "allowed_commands": ["uv run pytest -q"],
                    "forbidden_commands": ["git push"],
                    "requires_human_for": ["outside owned_files"],
                    "requires_llm_review_for": ["final handoff"],
                },
            }
        ],
        "team_admin": {
            "admin_id": "team-admin",
            "aggregation_policy": "collect_all_workers_then_review",
            "merge_policy": "review_before_merge",
            "completion_policy": "all_required_tasks_completed",
            "requires_human_for": ["missing worker output"],
            "requires_llm_review_for": ["final aggregation report"],
            "final_report_required": True,
        },
    }
    prd_path.write_bytes(orjson.dumps(payload))
    return prd_path


def _write_team_admin_report_artifact(tmp_path: Path) -> Path:
    report_path = tmp_path / "reports" / "team-admin.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "admin_id": "team-admin",
        "aggregation_state": "ready_for_ralph_review",
        "merge_ready": True,
        "final_report_required": True,
        "completed_workers": ["worker-1"],
        "missing_workers": [],
        "blocked_workers": [],
        "incomplete_workers": [],
        "requires_human_review": False,
        "requires_llm_review": True,
        "task_count": 1,
        "event_count": 2,
        "summary": "Team Admin collected worker-1 output.",
    }
    report_path.write_bytes(orjson.dumps(payload))
    return report_path


def _write_ralph_review_result_artifact(tmp_path: Path) -> Path:
    review_path = tmp_path / "reports" / "ralph-review.json"
    review_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "decision": "complete",
        "complete": True,
        "follow_up_required": False,
        "human_review_required": False,
        "merge_approved": True,
        "completed_workers": ["worker-1", "worker-2"],
        "follow_up_workers": [],
        "review_blockers": [],
        "summary": "Ralph accepted all completed worker results.",
    }
    review_path.write_bytes(orjson.dumps(payload))
    return review_path


def test_package_entrypoint_runs_help() -> None:
    completed_process = _run_agent_remote_command(["--help"])

    assert completed_process.returncode == 0
    assert "AI-friendly route guidance" in completed_process.stdout
    assert "Agent-facing control layer" in completed_process.stdout
    assert "runtime" in completed_process.stdout
    assert "cockpit" in completed_process.stdout
    assert "team" in completed_process.stdout
    assert "history" in completed_process.stdout
    assert "adapt" in completed_process.stdout
    assert "goal" in completed_process.stdout
    assert "hypergoal" in completed_process.stdout
    assert "ralph" in completed_process.stdout
    assert "ultrawork" in completed_process.stdout
    assert "version" in completed_process.stdout


def test_package_entrypoint_runs_runtime_help() -> None:
    completed_process = _run_agent_remote_command(["runtime", "--help"])

    assert completed_process.returncode == 0
    assert "status" in completed_process.stdout
    assert "active-modes" in completed_process.stdout
    assert "mode-status" in completed_process.stdout
    assert "mode-state" in completed_process.stdout


def test_package_entrypoint_runs_cockpit_help() -> None:
    completed_process = _run_agent_remote_command(["cockpit", "--help"])

    assert completed_process.returncode == 0
    assert "snapshot" in completed_process.stdout


def test_package_entrypoint_runs_cockpit_snapshot_help() -> None:
    completed_process = _run_agent_remote_command(["cockpit", "snapshot", "--help"])

    assert completed_process.returncode == 0
    assert "--cwd" in completed_process.stdout
    assert "--team" in completed_process.stdout


def test_cockpit_snapshot_outputs_repo_scoped_json(monkeypatch, tmp_path: Path) -> None:
    from omx_remote.cli_launcher import cockpit_cli
    from omx_remote.schemas.cockpit.snapshot_schemas import (
        CockpitLaneName,
        CockpitLaneSnapshot,
        CockpitLaneState,
        CockpitSnapshot,
    )

    async def fake_read_cockpit_snapshot(request):
        assert request.repo_root == str(tmp_path.resolve())
        assert request.team_names == ("team-alpha",)
        return CockpitSnapshot(
            repo_root=request.repo_root,
            runtime_summary="No active modes.",
            active_runtime_modes=(),
            contradictions=(),
            lanes=(
                CockpitLaneSnapshot(
                    name=CockpitLaneName.HYPERGOAL,
                    state=CockpitLaneState.PLANNED_ONLY,
                    summary="Hypergoal is template-only.",
                    recommended_next_action="use_hypergoal_template_only",
                ),
            ),
            safe_to_mutate=True,
            recommended_next_action="observe",
        )

    monkeypatch.setattr(cockpit_cli, "read_cockpit_snapshot", fake_read_cockpit_snapshot)

    result = CliRunner().invoke(
        app,
        ["cockpit", "snapshot", "--cwd", str(tmp_path), "--team", "team-alpha"],
    )

    assert result.exit_code == 0
    output = orjson.loads(result.stdout)
    assert output["repo_root"] == str(tmp_path.resolve())
    assert output["lanes"][0]["name"] == "hypergoal"


def test_team_cli_is_split_into_feature_launcher_modules() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    team_cli_path = repo_root / "src" / "omx_remote" / "cli_launcher" / "team_cli.py"
    team_launcher_dir = (
        repo_root / "src" / "omx_remote" / "cli_launcher" / "team_launcher"
    )
    expected_modules = {
        "team_read_cli.py",
        "team_message_cli.py",
        "team_task_cli.py",
        "team_approval_cli.py",
        "team_mailbox_cli.py",
        "team_shutdown_cli.py",
        "team_cleanup_cli.py",
        "team_admin_cli.py",
    }

    assert team_launcher_dir.is_dir()
    assert not (team_launcher_dir / "__init__.py").exists()
    assert expected_modules == {
        module_path.name for module_path in team_launcher_dir.glob("*.py")
    }
    assert len(team_cli_path.read_text().splitlines()) <= 80


def test_package_entrypoint_runs_team_help() -> None:
    completed_process = _run_agent_remote_command(["team", "--help"])

    assert completed_process.returncode == 0
    assert "status" in completed_process.stdout
    assert "await-event" in completed_process.stdout
    assert "tasks" in completed_process.stdout
    assert "events" in completed_process.stdout
    assert "worker-status" in completed_process.stdout
    assert "send-message" in completed_process.stdout
    assert "write-inbox" in completed_process.stdout
    assert "broadcast" in completed_process.stdout
    assert "create-task" in completed_process.stdout
    assert "read-task" in completed_process.stdout
    assert "transition-task-status" in completed_process.stdout
    assert "update-task" in completed_process.stdout
    assert "claim-task" in completed_process.stdout
    assert "release-task-claim" in completed_process.stdout
    assert "read-task-approval" in completed_process.stdout
    assert "write-task-approval" in completed_process.stdout
    assert "mailbox-mark-delivered" in completed_process.stdout
    assert "mailbox-mark-notified" in completed_process.stdout
    assert "write-shutdown-request" in completed_process.stdout
    assert "read-shutdown-ack" in completed_process.stdout
    assert "cleanup" in completed_process.stdout
    assert "orphan-cleanup" in completed_process.stdout
    assert "admin-report" in completed_process.stdout


def test_package_entrypoint_runs_team_admin_report_help() -> None:
    completed_process = _run_agent_remote_command(["team", "admin-report", "--help"])

    assert completed_process.returncode == 0
    assert "--team" in completed_process.stdout
    assert "--prd-path" in completed_process.stdout
    assert "--output-path" in completed_process.stdout


def test_team_admin_report_outputs_and_writes_report_json(monkeypatch, tmp_path: Path) -> None:
    from omx_remote.cli_launcher.team_launcher import team_admin_cli

    prd_path = _write_team_admin_prd_artifact(tmp_path)
    output_path = tmp_path / "reports" / "team-admin.json"

    async def fake_read_team_admin_aggregation_report(request):
        assert request.team_name == "alpha-team"
        assert request.ralph_prd_artifact.objective == "Collect Team Admin results from CLI."
        return TeamAdminAggregationReport(
            admin_id="team-admin",
            aggregation_state="ready_for_ralph_review",
            merge_ready=True,
            final_report_required=True,
            completed_workers=("worker-1",),
            missing_workers=(),
            blocked_workers=(),
            incomplete_workers=(),
            requires_human_review=False,
            requires_llm_review=True,
            task_count=1,
            event_count=1,
            summary="Team Admin collected 1/1 completed worker results; ready for Ralph review.",
        )

    monkeypatch.setattr(
        team_admin_cli,
        "read_team_admin_aggregation_report",
        fake_read_team_admin_aggregation_report,
    )

    result = CliRunner().invoke(
        app,
        [
            "team",
            "admin-report",
            "--team",
            "alpha-team",
            "--prd-path",
            str(prd_path),
            "--output-path",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    stdout_payload = orjson.loads(result.stdout)
    written_payload = orjson.loads(output_path.read_bytes())
    assert stdout_payload["aggregation_state"] == "ready_for_ralph_review"
    assert written_payload == stdout_payload


def test_package_entrypoint_runs_history_help() -> None:
    completed_process = _run_agent_remote_command(["history", "--help"])

    assert completed_process.returncode == 0
    assert "session-search" in completed_process.stdout


def test_package_entrypoint_runs_adapt_help() -> None:
    completed_process = _run_agent_remote_command(["adapt", "--help"])

    assert completed_process.returncode == 0
    assert "probe" in completed_process.stdout
    assert "status" in completed_process.stdout
    assert "envelope" in completed_process.stdout


def test_package_entrypoint_runs_goal_help() -> None:
    completed_process = _run_agent_remote_command(["goal", "--help"])

    assert completed_process.returncode == 0
    assert "Goal only" in completed_process.stdout
    assert "Goal → Ralph" in completed_process.stdout
    assert "Goal → Ralph → Team" in completed_process.stdout
    assert "Ralph → Team" in completed_process.stdout
    assert "Ultrawork only" in completed_process.stdout
    assert "Goal → Team" not in completed_process.stdout
    assert "Goal → Ultrawork" not in completed_process.stdout
    assert "Hypergoal" in completed_process.stdout
    assert "start" in completed_process.stdout
    assert "status" in completed_process.stdout
    assert "template" in completed_process.stdout
    assert "prepare-ralph" in completed_process.stdout
    assert "launch-ralph" not in completed_process.stdout
    assert "restore-lifecycle" in completed_process.stdout
    assert "operating-decision" in completed_process.stdout


def test_package_entrypoint_runs_goal_template_help() -> None:
    completed_process = _run_agent_remote_command(["goal", "template", "--help"])

    assert completed_process.returncode == 0
    assert "Codex /goal prompt scaffold" in completed_process.stdout


def test_package_entrypoint_runs_goal_template() -> None:
    completed_process = _run_agent_remote_command(["goal", "template"])

    assert completed_process.returncode == 0
    assert "# Codex /goal Prompt Template" in completed_process.stdout
    assert "Goal:" in completed_process.stdout
    assert "Context:" in completed_process.stdout
    assert "Constraints:" in completed_process.stdout
    assert "Done When:" in completed_process.stdout
    assert "Route guide:" in completed_process.stdout
    assert "Goal only" in completed_process.stdout
    assert "Goal → Ralph" in completed_process.stdout
    assert "Goal → Ralph → Team" in completed_process.stdout
    assert "Ralph → Team" in completed_process.stdout
    assert "Ultrawork only" in completed_process.stdout
    assert "Hypergoal" in completed_process.stdout
    assert "Goal → Ultrawork" not in completed_process.stdout


def test_package_entrypoint_runs_hypergoal_help() -> None:
    completed_process = _run_agent_remote_command(["hypergoal", "--help"])

    assert completed_process.returncode == 0
    assert "template" in completed_process.stdout


def test_package_entrypoint_runs_hypergoal_template() -> None:
    completed_process = _run_agent_remote_command(["hypergoal", "template"])

    assert completed_process.returncode == 0
    assert "# Hypergoal Deep-Work Scaffold" in completed_process.stdout
    assert "Focus window:" in completed_process.stdout
    assert "Recovery checklist:" in completed_process.stdout
    assert "Goal → Ultrawork" not in completed_process.stdout


def test_package_entrypoint_runs_goal_prepare_ralph_help() -> None:
    completed_process = _run_agent_remote_command(["goal", "prepare-ralph", "--help"])

    assert completed_process.returncode == 0
    assert "--source-path" in completed_process.stdout
    assert "--requested-slice" in completed_process.stdout
    assert "--constraint" in completed_process.stdout
    assert "--verification-expectation" in completed_process.stdout
    assert "--cwd" in completed_process.stdout
    source_path_block = completed_process.stdout.split("--source-path", 1)[1].split(
        "--requested-slice",
        1,
    )[0]
    requested_slice_block = completed_process.stdout.split("--requested-slice", 1)[
        1
    ].split("--constraint", 1)[0]
    constraint_block = completed_process.stdout.split("--constraint", 1)[1].split(
        "--verification-expectation",
        1,
    )[0]
    verification_block = completed_process.stdout.split("--verification-expectation", 1)[
        1
    ].split("--cwd", 1)[0]
    assert "[required]" in source_path_block
    assert "[required]" in requested_slice_block
    assert "[required]" not in constraint_block
    assert "[required]" in verification_block



def test_package_entrypoint_runs_goal_prepare_ralph_without_constraints(
    tmp_path: Path,
) -> None:
    _write_codex_goal_mirror_state(tmp_path)

    completed_process = _run_agent_remote_command(
        [
            "goal",
            "prepare-ralph",
            "--cwd",
            str(tmp_path),
            "--source-path",
            "AGENTS.md",
            "--requested-slice",
            "schema config and root base",
            "--verification-expectation",
            "targeted tests pass",
        ]
    )

    assert completed_process.returncode == 0, completed_process.stdout
    output = orjson.loads(completed_process.stdout)
    assert output["prompt_request"]["source_paths"] == ["AGENTS.md"]
    assert output["prompt_request"]["constraints"] == []
    assert output["prompt_request"]["verification_expectations"] == [
        "targeted tests pass"
    ]


def test_package_entrypoint_rejects_removed_goal_launch_ralph_help() -> None:
    completed_process = _run_agent_remote_command(["goal", "launch-ralph", "--help"])

    assert completed_process.returncode != 0
    assert "launch-ralph" in completed_process.stderr


def test_package_entrypoint_runs_goal_restore_lifecycle_help() -> None:
    completed_process = _run_agent_remote_command(["goal", "restore-lifecycle", "--help"])

    assert completed_process.returncode == 0
    assert "--goal-id" in completed_process.stdout
    assert "--cwd" in completed_process.stdout


def test_package_entrypoint_runs_goal_restore_lifecycle(tmp_path: Path) -> None:
    _write_goal_lifecycle_bundle(tmp_path)

    completed_process = _run_agent_remote_command([
        "goal",
        "restore-lifecycle",
        "--goal-id",
        "goal-cli",
        "--cwd",
        str(tmp_path),
    ])

    assert completed_process.returncode == 0
    output = orjson.loads(completed_process.stdout)
    assert output["bundle"]["goal_id"] == "goal-cli"
    assert output["next_resume_target"] == "ralph_post_team_review"
    assert output["ready_to_resume"] is True


def test_package_entrypoint_runs_goal_operating_decision_help() -> None:
    completed_process = _run_agent_remote_command(["goal", "operating-decision", "--help"])

    assert completed_process.returncode == 0
    assert "--goal-id" in completed_process.stdout
    assert "--team-name" in completed_process.stdout
    assert "--cwd" in completed_process.stdout


def test_package_entrypoint_runs_goal_operating_decision(tmp_path: Path) -> None:
    _write_goal_lifecycle_bundle(tmp_path)

    completed_process = _run_agent_remote_command([
        "goal",
        "operating-decision",
        "--goal-id",
        "goal-cli",
        "--team-name",
        "team-alpha",
        "--cwd",
        str(tmp_path),
    ])

    assert completed_process.returncode == 0
    output = orjson.loads(completed_process.stdout)
    assert output["goal_id"] == "goal-cli"
    assert output["current_stage"] == "ralph_post_team_review_pending"
    assert output["next_action"] == "run_ralph_post_team_review"
    assert output["available_evidence"] == [
        "goal_lifecycle_artifact",
        "team_admin_aggregation_report",
    ]
    assert output["missing_evidence"] == []
    assert output["safe_to_mutate"] is False


def test_package_entrypoint_runs_goal_lifecycle_decision_help() -> None:
    completed_process = _run_agent_remote_command(["goal", "lifecycle-decision", "--help"])

    assert completed_process.returncode == 0
    assert "--goal-id" in completed_process.stdout
    assert "--ralph-review" in completed_process.stdout
    assert "--cwd" in completed_process.stdout
    assert "--output-path" in completed_process.stdout


def test_goal_lifecycle_decision_outputs_writes_and_updates_bundle(tmp_path: Path) -> None:
    _write_goal_lifecycle_bundle(tmp_path)
    ralph_review_path = _write_ralph_review_result_artifact(tmp_path)
    output_path = tmp_path / "reports" / "goal-lifecycle-decision.json"

    completed_process = _run_agent_remote_command(
        [
            "goal",
            "lifecycle-decision",
            "--goal-id",
            "goal-cli",
            "--ralph-review",
            str(ralph_review_path),
            "--cwd",
            str(tmp_path),
            "--output-path",
            str(output_path),
        ]
    )

    assert completed_process.returncode == 0, completed_process.stdout
    output = orjson.loads(completed_process.stdout)
    assert output["goal_id"] == "goal-cli"
    assert output["action"] == "close_goal"
    assert output["ready_to_close"] is True
    assert orjson.loads(output_path.read_bytes()) == output

    bundle_path = tmp_path / ".agent-remote" / "state" / "goal-lifecycle" / "goal-cli.json"
    bundle = orjson.loads(bundle_path.read_bytes())
    assert bundle["ralph_review_result"]["decision"] == "complete"
    assert bundle["lifecycle_decision"]["action"] == "close_goal"


def test_goal_lifecycle_decision_initializes_bundle_from_goal_mirror(tmp_path: Path) -> None:
    _write_codex_goal_mirror_state(tmp_path)
    ralph_review_path = _write_ralph_review_result_artifact(tmp_path)

    completed_process = _run_agent_remote_command(
        [
            "goal",
            "lifecycle-decision",
            "--goal-id",
            "goal-cli",
            "--ralph-review",
            str(ralph_review_path),
            "--cwd",
            str(tmp_path),
        ]
    )

    assert completed_process.returncode == 0, completed_process.stdout
    output = orjson.loads(completed_process.stdout)
    assert output["action"] == "close_goal"

    bundle_path = tmp_path / ".agent-remote" / "state" / "goal-lifecycle" / "goal-cli.json"
    bundle = orjson.loads(bundle_path.read_bytes())
    assert bundle["goal_id"] == "goal-cli"
    assert bundle["mirror_state"]["objective_text"] == "Prepare a Ralph handoff from CLI."
    assert bundle["ralph_review_result"]["decision"] == "complete"
    assert bundle["lifecycle_decision"]["action"] == "close_goal"


def test_package_entrypoint_runs_goal_start_help() -> None:
    completed_process = _run_agent_remote_command(["goal", "start", "--help"])

    assert completed_process.returncode == 0
    assert "--objective" in completed_process.stdout
    assert "--execution-shape" in completed_process.stdout
    assert "--review-policy" in completed_process.stdout
    assert "--team-worker-count" in completed_process.stdout


def test_package_entrypoint_runs_ralph_help() -> None:
    completed_process = _run_agent_remote_command(["ralph", "--help"])

    assert completed_process.returncode == 0
    assert "snapshot" in completed_process.stdout
    assert "startability" in completed_process.stdout
    assert "launch" in completed_process.stdout
    assert "launch-team" in completed_process.stdout
    assert "resume" in completed_process.stdout
    assert "cleanup-stale" in completed_process.stdout


def test_package_entrypoint_runs_ralph_launch_help() -> None:
    completed_process = _run_agent_remote_command(["ralph", "launch", "--help"])

    assert completed_process.returncode == 0
    assert "--task" in completed_process.stdout
    assert "--inherit-stdio" in completed_process.stdout


def test_package_entrypoint_runs_ralph_launch_team_help() -> None:
    completed_process = _run_agent_remote_command(["ralph", "launch-team", "--help"])

    assert completed_process.returncode == 0
    assert "--allow-non-tty" in completed_process.stdout
    assert "--inherit-stdio" in completed_process.stdout
    assert "--plan-only" in completed_process.stdout


def test_ralph_launch_team_plan_only_writes_assignment_dag_without_invoking_omx(
    monkeypatch, tmp_path: Path
) -> None:
    from omx_remote.cli_launcher import ralph_cli

    monkeypatch.chdir(tmp_path)
    _write_team_admin_prd_artifact(tmp_path)

    def fail_if_invoked(command: list[str]):
        raise AssertionError(f"OMX should not be invoked in plan-only mode: {command}")

    monkeypatch.setattr(ralph_cli, "_run_omx_command", fail_if_invoked)
    monkeypatch.setattr(ralph_cli, "_run_omx_command_inherited_stdio", fail_if_invoked)

    result = CliRunner().invoke(
        app,
        ["ralph", "launch-team", "--allow-non-tty", "--plan-only"],
    )

    assert result.exit_code == 0, result.stdout
    output = orjson.loads(result.stdout)
    assert output["command"] == [
        "team",
        "1",
        "Collect Team Admin results from CLI.",
    ]
    assert output["planned_only"] is True
    dag_path = next((tmp_path / ".omx" / "plans").glob("team-dag-*-ralph-team.json"))
    dag_payload = orjson.loads(dag_path.read_bytes())
    assert dag_payload["worker_policy"]["requested_count"] == 1
    assert dag_payload["nodes"][0]["id"] == "worker-1"
    assert dag_payload["nodes"][0]["description"].startswith("Lane: worker-1 lane")
    assert dag_payload["nodes"][0]["authorization"]["policy"] == "llm_review"


def test_package_entrypoint_runs_ralph_review_team_help() -> None:
    completed_process = _run_agent_remote_command(["ralph", "review-team", "--help"])

    assert completed_process.returncode == 0
    assert "--prd-path" in completed_process.stdout
    assert "--admin-report" in completed_process.stdout
    assert "--output-path" in completed_process.stdout


def test_ralph_review_team_outputs_and_writes_review_json(tmp_path: Path) -> None:
    prd_path = _write_team_admin_prd_artifact(tmp_path)
    admin_report_path = _write_team_admin_report_artifact(tmp_path)
    output_path = tmp_path / "reports" / "ralph-review-output.json"

    completed_process = _run_agent_remote_command(
        [
            "ralph",
            "review-team",
            "--prd-path",
            str(prd_path),
            "--admin-report",
            str(admin_report_path),
            "--output-path",
            str(output_path),
        ]
    )

    assert completed_process.returncode == 0, completed_process.stdout
    output = orjson.loads(completed_process.stdout)
    assert output["decision"] == "complete"
    assert output["merge_approved"] is True
    assert output["completed_workers"] == ["worker-1"]
    assert orjson.loads(output_path.read_bytes()) == output


def test_ralph_launch_can_inherit_stdio_for_interactive_omx(monkeypatch) -> None:
    seen_command: list[str] = []

    def fake_build_ralph_launch_plan(
        task: str,
        force_cleanup: bool,
        allow_non_tty: bool,
    ):
        assert task == "Launch Ralph interactively."
        assert force_cleanup is False
        assert allow_non_tty is False
        return ["ralph", "--prd", "Launch Ralph interactively."], []

    def fake_run_omx_command_inherited_stdio(command: list[str]):
        nonlocal seen_command
        seen_command = command
        from omx_remote.schemas.invoke.command_schemas import OmxCommandResult

        return OmxCommandResult(exit_code=0, stdout="", stderr="")

    monkeypatch.setattr(
        "omx_remote.cli_launcher.ralph_cli.build_ralph_launch_plan",
        fake_build_ralph_launch_plan,
    )
    monkeypatch.setattr(
        "omx_remote.cli.run_omx_command_inherited_stdio",
        fake_run_omx_command_inherited_stdio,
    )

    result = CliRunner().invoke(
        app,
        [
            "ralph",
            "launch",
            "--task",
            "Launch Ralph interactively.",
            "--inherit-stdio",
        ],
    )

    assert result.exit_code == 0
    assert seen_command == ["ralph", "--prd", "Launch Ralph interactively."]


def test_ralph_startability_outputs_json(monkeypatch) -> None:
    async def fake_read_runtime_mode_state(request):
        _ = request
        return RuntimeModeStateSnapshot(
            mode="ralph",
            exists=True,
            state={"active": False, "mode": "ralph"},
        )

    async def fake_read_runtime_mode_status(request):
        _ = request
        return RuntimeModeStatusResult(
            requested_mode="ralph",
            found=True,
            mode_snapshot=RuntimeModeStatusSnapshot(
                name="ralph",
                is_active=False,
                phase="cancelled",
                state_path="/tmp/ralph-state.json",
            ),
        )

    monkeypatch.setattr("omx_remote.cli.read_runtime_mode_state", fake_read_runtime_mode_state)
    monkeypatch.setattr("omx_remote.cli.read_runtime_mode_status", fake_read_runtime_mode_status)

    result = CliRunner().invoke(app, ["ralph", "startability"])

    assert result.exit_code == 0
    output = orjson.loads(result.stdout)
    assert output["mode_state"]["mode"] == "ralph"
    assert output["mode_status"]["requested_mode"] == "ralph"


def test_package_entrypoint_runs_ultrawork_help() -> None:
    completed_process = _run_agent_remote_command(["ultrawork", "--help"])

    assert completed_process.returncode == 0
    assert "launch" in completed_process.stdout
    assert "resume" in completed_process.stdout
    assert "cleanup-stale" in completed_process.stdout


def test_package_entrypoint_runs_version() -> None:
    completed_process = _run_agent_remote_command(["version"])

    assert completed_process.returncode == 0
    assert "agent-remote 0.1.0" in completed_process.stdout
