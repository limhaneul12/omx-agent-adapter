import sys
from pathlib import Path

import orjson
import pytest
from typer.testing import CliRunner

from omx_remote.cli import app
from omx_remote.runtime.commands.blueprints.adapter_ops_blueprints import (
    ADAPTER_OPS_COMMAND_IDS,
)
from omx_remote.runtime.commands.blueprints.consolidated_lifecycle_blueprints import (
    PUBLIC_WORKFLOW_COMMAND_IDS,
)

EXPECTED_PUBLIC_RISKS = {
    "route-next": "read_only",
    "research-brief": "external_network",
    "idea-to-prd": "long_running",
    "implementation-kickoff": "launches_runtime",
    "team-sync": "read_only",
    "integration-plan": "long_running",
    "review-gate": "long_running",
    "release-readiness": "writes_files",
    "company-run": "launches_runtime",
}


def _write_agent_config(workspace: Path) -> None:
    agent_blocks = [
        f"""
[agents.{agent_id}]
enabled = true
provider = "codex"
role = "{agent_id}"
model = "gpt-5.5"
effort = "xhigh"
persona = "Test {agent_id} persona."
""".strip()
        for agent_id in (
            "route_strategist",
            "research_analyst",
            "implementation_architect",
            "integration_steward",
            "quality_gatekeeper",
        )
    ]
    (workspace / ".comx-agent.toml").write_text(
        "\n\n".join(agent_blocks), encoding="utf-8"
    )


def test_commands_list_shows_nine_public_workflows_and_adapter_ops(
    tmp_path: Path,
) -> None:
    result = CliRunner().invoke(
        app,
        ["commands", "list", "--cwd", str(tmp_path), "--json"],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["builtin_count"] == 14
    assert payload["public_workflow_commands"] == 9
    assert payload["lifecycle_commands"] == 8
    assert payload["macro_commands"] == 1
    assert payload["adapter_ops_commands"] == 5
    public_ids = {
        command["id"]
        for command in payload["commands"]
        if command["namespace"] == "workflow"
        and command["category"] in {"lifecycle", "macro"}
    }
    adapter_ids = {
        command["id"]
        for command in payload["commands"]
        if command["namespace"] == "adapter-ops"
    }
    assert public_ids == set(PUBLIC_WORKFLOW_COMMAND_IDS)
    assert adapter_ids == set(ADAPTER_OPS_COMMAND_IDS)


def test_commands_validate_outputs_grouped_counts(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        ["commands", "validate", "--cwd", str(tmp_path), "--json"],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload == {
        "valid": True,
        "command_count": 14,
        "builtin_count": 14,
        "repo_count": 0,
        "public_workflow_commands": 9,
        "lifecycle_commands": 8,
        "macro_commands": 1,
        "adapter_ops_commands": 5,
    }


@pytest.mark.parametrize("command_id", PUBLIC_WORKFLOW_COMMAND_IDS)
def test_commands_show_outputs_public_workflow_recipe(
    tmp_path: Path, command_id: str
) -> None:
    result = CliRunner().invoke(
        app,
        [
            "commands",
            "show",
            f"builtin:{command_id}",
            "--cwd",
            str(tmp_path),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["recipe"]["id"] == command_id
    assert payload["recipe"]["source"] == "builtin"
    assert payload["recipe"]["namespace"] == "workflow"
    assert payload["recipe"]["risk"] == EXPECTED_PUBLIC_RISKS[command_id]
    assert payload["recipe"]["steps"]


def test_commands_show_outputs_adapter_ops_recipe_with_canonical_id(
    tmp_path: Path,
) -> None:
    result = CliRunner().invoke(
        app,
        [
            "commands",
            "show",
            "builtin:adapter-ops mcp-audit",
            "--cwd",
            str(tmp_path),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["recipe"]["id"] == "mcp-audit"
    assert payload["recipe"]["public_id"] == "adapter-ops:mcp-audit"
    assert payload["recipe"]["display_id"] == "adapter-ops mcp-audit"
    assert payload["recipe"]["namespace"] == "adapter-ops"
    assert payload["recipe"]["category"] == "maintenance"


def test_commands_show_rejects_adapter_ops_alias_spellings(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "commands",
            "show",
            "builtin:adapter-ops/mcp-audit",
            "--cwd",
            str(tmp_path),
            "--json",
        ],
    )

    assert result.exit_code == 2
    payload = orjson.loads(result.stdout)
    assert "No command named" in payload["error"]


@pytest.mark.parametrize("command_id", PUBLIC_WORKFLOW_COMMAND_IDS)
def test_run_public_workflow_dry_run_outputs_plan(
    tmp_path: Path, command_id: str
) -> None:
    _write_agent_config(tmp_path)
    result = CliRunner().invoke(
        app,
        [
            "run",
            f"builtin:{command_id}",
            "--cwd",
            str(tmp_path),
            "--dry-run",
            "--task",
            "smoke task",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["command_id"] == command_id
    assert payload["qualified_id"] == f"builtin:{command_id}"
    assert payload["namespace"] == "workflow"
    assert payload["dry_run"] is True
    assert payload["risk"] == EXPECTED_PUBLIC_RISKS[command_id]
    assert payload["steps"]
    assert payload["blocked_reasons"] == []
    assert "smoke task" in orjson.dumps(payload["steps"]).decode()


def test_run_company_run_dry_run_renders_macro_gates_without_execution(
    tmp_path: Path,
) -> None:
    _write_agent_config(tmp_path)
    result = CliRunner().invoke(
        app,
        [
            "run",
            "builtin:company-run",
            "--cwd",
            str(tmp_path),
            "--dry-run",
            "--task",
            "build an agent company",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    plan_text = orjson.dumps(payload).decode()
    for term in (
        "company-run",
        "research-vote.md",
        "proceed-vote.md",
        "prd-readiness.md",
        "team-plan.md",
        "review-loop.md",
        "release-closeout.md",
        "company_orchestrator",
        "research_council",
        "executive_council",
        "alexandria_mcp",
        "omx_team",
        "Alexandria MCP tools",
    ):
        assert term in plan_text
    assert payload["steps"][-1]["command"] == "omx_team"
    assert payload["steps"][-1]["native_argv"] == ["omx", "team", "--help"]


def test_run_adapter_ops_dry_run_outputs_maintenance_plan(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "run",
            "builtin:adapter-ops mcp-audit",
            "--cwd",
            str(tmp_path),
            "--dry-run",
            "--task",
            "audit MCP setup",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["command_id"] == "adapter-ops mcp-audit"
    assert payload["qualified_id"] == "builtin:adapter-ops mcp-audit"
    assert payload["namespace"] == "adapter-ops"
    assert payload["category"] == "maintenance"
    assert payload["dry_run"] is True
    assert payload["steps"][0]["prompt_exists"] is True


def test_unknown_command_invocation_returns_missing_command_error(
    tmp_path: Path,
) -> None:
    result = CliRunner().invoke(
        app,
        [
            "run",
            "builtin:not-a-command",
            "--cwd",
            str(tmp_path),
            "--dry-run",
            "--json",
        ],
    )

    assert result.exit_code == 2
    payload = orjson.loads(result.stdout)
    assert payload["error"] == "No command named builtin:not-a-command was found."


def test_run_repo_command_dry_run_reads_prompt_file(tmp_path: Path) -> None:
    prompt_path = tmp_path / "prompts" / "review.md"
    prompt_path.parent.mkdir()
    prompt_path.write_text("Review the diff.")
    (tmp_path / ".comx-agent.toml").write_text(
        """
[commands.codex_review]
description = "Review current diff."
provider = "codex"
mode = "exec"
prompt_file = "prompts/review.md"
""".strip()
    )

    result = CliRunner().invoke(
        app,
        ["run", "repo:codex_review", "--cwd", str(tmp_path), "--dry-run", "--json"],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["source"] == "repo"
    assert payload["steps"][0]["prompt_exists"] is True
    assert payload["steps"][0]["prompt_file"] == str(prompt_path)


def test_run_one_off_prompt_file_dry_run(tmp_path: Path) -> None:
    prompt_path = tmp_path / "task.md"
    prompt_path.write_text("Do the task.")

    result = CliRunner().invoke(
        app,
        [
            "run",
            "--provider",
            "codex",
            "--prompt-file",
            str(prompt_path),
            "--cwd",
            str(tmp_path),
            "--dry-run",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["command_id"] == "one-off-prompt"
    assert payload["steps"][0]["prompt_exists"] is True


def test_run_requires_dry_run_or_execute(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        ["run", "builtin:review-gate", "--cwd", str(tmp_path), "--json"],
    )

    assert result.exit_code == 2
    payload = orjson.loads(result.stdout)
    assert "Pass --dry-run" in payload["error"]


def test_run_repo_local_command_execute_outputs_actual_result(tmp_path: Path) -> None:
    command = f"""
[commands.local_echo]
description = "Run local echo."
risk = "read_only"
steps = [
  {{ command = "local", argv = ["{sys.executable}", "-c", "print('hello')"] }},
]
""".strip()
    (tmp_path / ".comx-agent.toml").write_text(command)

    result = CliRunner().invoke(
        app,
        [
            "run",
            "repo:local_echo",
            "--cwd",
            str(tmp_path),
            "--execute",
            "--autonomy",
            "agent",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["status"] == "succeeded"
    assert payload["steps"][0]["attempts"][0]["exit_code"] == 0
    assert (
        tmp_path / ".comx-agent" / "runs" / payload["run_id"] / "run.json"
    ).exists()


def test_run_execute_failed_actual_result_returns_nonzero(tmp_path: Path) -> None:
    command = f"""
[commands.local_fail]
description = "Run local failure."
risk = "read_only"
steps = [
  {{ command = "local", argv = ["{sys.executable}", "-c", "raise SystemExit(5)"] }},
]
""".strip()
    (tmp_path / ".comx-agent.toml").write_text(command)

    result = CliRunner().invoke(
        app,
        [
            "run",
            "repo:local_fail",
            "--cwd",
            str(tmp_path),
            "--execute",
            "--autonomy",
            "agent",
            "--max-attempts",
            "1",
            "--json",
        ],
    )

    assert result.exit_code == 1
    payload = orjson.loads(result.stdout)
    assert payload["status"] == "failed"


def test_run_execute_requires_action_returns_soft_stop_code(tmp_path: Path) -> None:
    command = """
[commands.prompt_wait]
description = "Wait for handoff."
risk = "read_only"
steps = [
  { command = "prompt_only", inline_prompt = "Wait for agent action.", expected_artifacts = ["notes/handoff.md"] },
]
""".strip()
    (tmp_path / ".comx-agent.toml").write_text(command)

    result = CliRunner().invoke(
        app,
        [
            "run",
            "repo:prompt_wait",
            "--cwd",
            str(tmp_path),
            "--execute",
            "--autonomy",
            "agent",
            "--json",
        ],
    )

    assert result.exit_code == 3
    payload = orjson.loads(result.stdout)
    assert payload["status"] == "requires_agent_action"


def test_run_execute_requires_explicit_autonomy(tmp_path: Path) -> None:
    command = f"""
[commands.local_echo]
description = "Run local echo."
risk = "read_only"
steps = [
  {{ command = "local", argv = ["{sys.executable}", "-c", "print('hello')"] }},
]
""".strip()
    (tmp_path / ".comx-agent.toml").write_text(command)

    result = CliRunner().invoke(
        app,
        ["run", "repo:local_echo", "--cwd", str(tmp_path), "--execute", "--json"],
    )

    assert result.exit_code == 2
    payload = orjson.loads(result.stdout)
    assert "--autonomy agent" in payload["error"]
