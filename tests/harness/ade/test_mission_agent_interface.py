from pathlib import Path

import orjson
from comx_harness.cli import app
from comx_harness.schemas.mission_schemas import MissionRequest
from comx_harness.shared.harness_enums.mission_enums import MissionExecutionProfile
from typer.testing import CliRunner

runner = CliRunner()


def _mission(workspace: Path) -> MissionRequest:
    return MissionRequest(
        mission_id="agent-mission-readonly",
        controller_id="agent-cli-test",
        objective="Inspect the workspace without modifying it.",
        workspace=str(workspace.resolve()),
        execution_profile=MissionExecutionProfile.CODEX_NATIVE,
    )


def test_agent_mission_commands_plan_validate_and_execute_foreground(
    tmp_path: Path,
    fake_provider_path: Path,
) -> None:
    del fake_provider_path
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    request = _mission(workspace)
    request_path = tmp_path / "mission.json"
    request_path.write_text(request.model_dump_json(indent=2), encoding="utf-8")

    plan_result = runner.invoke(app, ["agent", "plan-mission", str(request_path)])
    assert plan_result.exit_code == 0
    plan = orjson.loads(plan_result.stdout)
    assert plan["schema_version"] == "mission-plan.v1"
    assert plan["request"]["mission_id"] == request.mission_id
    assert [stage["stage_id"] for stage in plan["strategy"]["stages"]] == [
        "primary-run",
        "finish",
    ]

    validation_result = runner.invoke(
        app,
        ["agent", "validate-mission", str(request_path)],
    )
    assert validation_result.exit_code == 0
    validation = orjson.loads(validation_result.stdout)
    assert validation["valid"] is True
    assert validation["strategy_validation"]["valid"] is True

    execution_result = runner.invoke(
        app,
        ["agent", "execute-mission", str(request_path), "--foreground"],
    )
    assert execution_result.exit_code == 0
    record = orjson.loads(execution_result.stdout)
    assert record["definition"]["strategy_id"] == request.mission_id
    assert record["status"] == "succeeded"
    assert [stage["status"] for stage in record["stages"]] == [
        "succeeded",
        "succeeded",
    ]

    mission_root = workspace / ".comx-agent" / "v2" / "missions" / request.mission_id
    assert (mission_root / "mission.json").is_file()
    assert (mission_root / "git-before.json").is_file()
    assert (mission_root / "git-policy-evidence.json").is_file()

    status_result = runner.invoke(
        app,
        ["agent", "mission-status", str(workspace), request.mission_id],
    )
    assert status_result.exit_code == 0
    status = orjson.loads(status_result.stdout)
    assert status["mission"]["strategy_id"] == request.mission_id
    assert status["strategy"]["status"] == "succeeded"
    assert status["git_policy_evidence"]["commit_created"] is False
    assert status["git_policy_evidence"]["branch_changed"] is False

    events_result = runner.invoke(
        app,
        ["agent", "mission-events", str(workspace), request.mission_id],
    )
    assert events_result.exit_code == 0
    events = orjson.loads(events_result.stdout)
    assert events["strategy_events"]["strategy_id"] == request.mission_id
    assert events["strategy_events"]["events"]

    artifacts_result = runner.invoke(
        app,
        ["agent", "mission-artifacts", str(workspace), request.mission_id],
    )
    assert artifacts_result.exit_code == 0
    artifacts = orjson.loads(artifacts_result.stdout)
    assert artifacts["strategy_artifacts"]["strategy_id"] == request.mission_id
    assert artifacts["strategy_artifacts"]["artifacts"]


def test_agent_mission_cli_rejects_auto_profile(tmp_path: Path) -> None:
    request_path = tmp_path / "invalid-mission.json"
    request_path.write_text(
        orjson.dumps(
            {
                "mission_id": "no-auto-router",
                "objective": "Do not infer an execution profile.",
                "workspace": str(tmp_path),
                "execution_profile": "auto",
            }
        ).decode(),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["agent", "plan-mission", str(request_path)])

    assert result.exit_code != 0
    assert "execution_profile" in result.output
