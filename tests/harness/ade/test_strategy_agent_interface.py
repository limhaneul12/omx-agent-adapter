from __future__ import annotations

import time
from pathlib import Path

import orjson
from comx_harness.cli import app
from comx_harness.schemas.strategy_schemas import StrategyDefinition, StrategyStage
from comx_harness.shared.harness_enums.strategy_enums import StrategyNodeType
from typer.testing import CliRunner

runner = CliRunner()


def _finish_only_strategy(workspace: Path) -> StrategyDefinition:
    return StrategyDefinition(
        strategy_id="detached-finish-only",
        controller_id="agent-cli-test",
        mission="Verify detached Strategy process separation without provider cost.",
        stages=(
            StrategyStage(
                stage_id="finish",
                node_type=StrategyNodeType.FINISH,
                objective="Finish after validating an empty dependency set.",
                workspace=str(workspace.resolve()),
            ),
        ),
    )


def test_agent_strategy_commands_validate_detach_and_reopen_state(
    tmp_path: Path,
    fake_provider_path: Path,
) -> None:
    del fake_provider_path
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    definition = _finish_only_strategy(workspace)
    request_path = tmp_path / "strategy.json"
    request_path.write_text(definition.model_dump_json(indent=2), encoding="utf-8")

    validation_result = runner.invoke(
        app,
        ["agent", "validate-strategy", str(request_path)],
    )
    assert validation_result.exit_code == 0
    validation = orjson.loads(validation_result.stdout)
    assert validation["valid"] is True

    launched_result = runner.invoke(
        app,
        ["agent", "execute-strategy", str(request_path)],
    )
    assert launched_result.exit_code == 0
    launched = orjson.loads(launched_result.stdout)
    assert launched["status"] in {"running", "succeeded"}
    assert launched["pid"] is not None

    current = launched
    deadline = time.monotonic() + 10.0
    while current["status"] == "running" and time.monotonic() < deadline:
        time.sleep(0.05)
        launch_result = runner.invoke(
            app,
            [
                "agent",
                "strategy-launch",
                str(workspace),
                definition.strategy_id,
            ],
        )
        assert launch_result.exit_code == 0
        current = orjson.loads(launch_result.stdout)

    assert current["status"] == "succeeded"

    status_result = runner.invoke(
        app,
        [
            "agent",
            "strategy-status",
            str(workspace),
            definition.strategy_id,
        ],
    )
    events_result = runner.invoke(
        app,
        [
            "agent",
            "strategy-events",
            str(workspace),
            definition.strategy_id,
        ],
    )
    artifacts_result = runner.invoke(
        app,
        [
            "agent",
            "strategy-artifacts",
            str(workspace),
            definition.strategy_id,
        ],
    )

    assert status_result.exit_code == 0
    assert events_result.exit_code == 0
    assert artifacts_result.exit_code == 0
    status = orjson.loads(status_result.stdout)
    events = orjson.loads(events_result.stdout)
    artifacts = orjson.loads(artifacts_result.stdout)
    assert status["status"] == "succeeded"
    assert status["stages"][0]["status"] == "succeeded"
    assert events["events"][0]["message"] == "created"
    assert events["events"][-1]["message"] == "succeeded"
    assert artifacts["artifacts"] == []


def test_agent_capabilities_exposes_readiness_states(
    fake_provider_path: Path,
) -> None:
    del fake_provider_path
    result = runner.invoke(app, ["agent", "capabilities"])

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["schema_version"] == "capability-matrix.v1"
    for provider in payload["providers"]:
        assert set(provider["readiness"]) == {
            "installed",
            "authenticated",
            "execution_ready",
            "unavailable",
            "detail",
        }
