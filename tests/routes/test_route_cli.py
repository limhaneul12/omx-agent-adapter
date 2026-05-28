from pathlib import Path

import orjson
from typer.testing import CliRunner

import omx_remote.cli_launcher.route_cli as route_cli
from omx_remote.cli import app
from omx_remote.schemas.cockpit.capability_snapshot_schemas import (
    CockpitAgentConfigSummary,
    CockpitCapabilitiesSnapshot,
    CockpitCapabilityCommand,
    CockpitCommandRecipeSummary,
    CockpitRuntimeCapability,
)
from omx_remote.schemas.runtime.status_schemas import ActiveRuntimeModes


def _capabilities() -> CockpitCapabilitiesSnapshot:
    return CockpitCapabilitiesSnapshot(
        codex=CockpitRuntimeCapability(
            name="codex",
            available=True,
            executable_path="/usr/bin/codex",
            version="codex 0.133.0",
            commands=(
                CockpitCapabilityCommand(
                    name="exec_json",
                    available=True,
                    detail="codex exec --json is available.",
                ),
            ),
        ),
        omx=CockpitRuntimeCapability(
            name="omx",
            available=True,
            executable_path="/usr/bin/omx",
            version="omx 0.18.0",
            commands=(
                CockpitCapabilityCommand(
                    name="ultragoal",
                    available=True,
                    detail="omx ultragoal --help succeeded.",
                ),
            ),
        ),
    )


def test_route_recommend_cli_outputs_json_policy(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(route_cli, "read_cockpit_capabilities", lambda: _capabilities())

    async def fake_read_active_runtime_modes() -> ActiveRuntimeModes:
        return ActiveRuntimeModes(active_modes=())

    monkeypatch.setattr(
        route_cli,
        "read_active_runtime_modes",
        fake_read_active_runtime_modes,
    )
    monkeypatch.setattr(
        route_cli,
        "summarize_cockpit_agent_config",
        lambda cwd: CockpitAgentConfigSummary(
            config_path=str(tmp_path / ".agent-remote.toml"),
            total_count=0,
            enabled_count=0,
            disabled_count=0,
            enabled_agent_ids=(),
            warnings=(),
        ),
    )
    monkeypatch.setattr(
        route_cli,
        "summarize_cockpit_command_recipes",
        lambda cwd: CockpitCommandRecipeSummary(
            available_count=2,
            builtin_count=2,
            repo_count=0,
            qualified_ids=("builtin:review-diff", "builtin:verify-handoff"),
            warnings=(),
        ),
    )

    result = CliRunner().invoke(
        app,
        [
            "route",
            "recommend",
            "--task",
            "review current diff",
            "--cwd",
            str(tmp_path),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["classification"]["task_type"] == "review"
    assert payload["recommendations"][0]["route"] == "project_command"
    assert payload["recommendations"][0]["command_id"] == "builtin:review-diff"


def test_route_explain_outputs_json_description() -> None:
    result = CliRunner().invoke(
        app,
        ["route", "explain", "omx-ultragoal", "--json"],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["route"] == "omx_ultragoal"
    assert "durable" in payload["summary"]
