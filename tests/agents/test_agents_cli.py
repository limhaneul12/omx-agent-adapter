from pathlib import Path

import orjson
from typer.testing import CliRunner

from omx_remote.cli import app


def _write_agent_config(config_path: Path) -> None:
    config_path.write_text(
        """
[agents.architect]
enabled = true
provider = "codex"
role = "architect"
model = "gpt-5.5"
effort = "high"
persona = "Design typed boundaries."

[agents.reviewer]
enabled = false
provider = "codex"
role = "reviewer"
model = "gpt-5.5"
effort = "xhigh"
persona = "Review diffs."
""".strip()
    )


def test_agents_list_json_includes_disabled_by_default(tmp_path: Path) -> None:
    _write_agent_config(tmp_path / ".comx-agent.toml")

    result = CliRunner().invoke(
        app,
        ["agents", "list", "--cwd", str(tmp_path), "--json"],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert [agent["id"] for agent in payload["agents"]] == ["architect", "reviewer"]
    assert payload["enabled_count"] == 1
    assert payload["disabled_count"] == 1


def test_agents_list_enabled_only_filters_disabled_agents(tmp_path: Path) -> None:
    _write_agent_config(tmp_path / ".comx-agent.toml")

    result = CliRunner().invoke(
        app,
        ["agents", "list", "--cwd", str(tmp_path), "--enabled-only", "--json"],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert [agent["id"] for agent in payload["agents"]] == ["architect"]


def test_agents_list_human_output_marks_enabled_and_disabled(tmp_path: Path) -> None:
    _write_agent_config(tmp_path / ".comx-agent.toml")

    result = CliRunner().invoke(app, ["agents", "list", "--cwd", str(tmp_path)])

    assert result.exit_code == 0
    assert "architect" in result.stdout
    assert "enabled" in result.stdout
    assert "reviewer" in result.stdout
    assert "disabled" in result.stdout


def test_agents_show_outputs_one_agent_json(tmp_path: Path) -> None:
    _write_agent_config(tmp_path / ".comx-agent.toml")

    result = CliRunner().invoke(
        app,
        ["agents", "show", "architect", "--cwd", str(tmp_path), "--json"],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["agent"]["id"] == "architect"
    assert payload["agent"]["enabled"] is True


def test_agents_show_missing_agent_exits_nonzero(tmp_path: Path) -> None:
    _write_agent_config(tmp_path / ".comx-agent.toml")

    result = CliRunner().invoke(
        app,
        ["agents", "show", "missing", "--cwd", str(tmp_path), "--json"],
    )

    assert result.exit_code == 2
    payload = orjson.loads(result.stdout)
    assert "No agent named missing" in payload["error"]


def test_agents_validate_reports_valid_config(tmp_path: Path) -> None:
    _write_agent_config(tmp_path / ".comx-agent.toml")

    result = CliRunner().invoke(
        app,
        ["agents", "validate", "--cwd", str(tmp_path), "--json"],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["valid"] is True
    assert payload["agent_count"] == 2


def test_agents_validate_exits_nonzero_on_schema_error(tmp_path: Path) -> None:
    (tmp_path / ".comx-agent.toml").write_text(
        """
[agents.architect]
enabled = true
provider = "codex"
role = "architect"
model = "gpt-5.5"
effort = "high"
""".strip()
    )

    result = CliRunner().invoke(
        app,
        ["agents", "validate", "--cwd", str(tmp_path), "--json"],
    )

    assert result.exit_code == 2
    payload = orjson.loads(result.stdout)
    assert payload["valid"] is False
    assert "persona" in payload["error"]


def _write_codex_contract(codex_home: Path) -> None:
    agents_dir = codex_home / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "sample.toml").write_text(
        '''
name = "sample"
description = "Sample agent"
model = "gpt-5.5"
model_reasoning_effort = "medium"
developer_instructions = """Act as sample."""
'''.strip(),
        encoding="utf-8",
    )


def test_agents_plan_apply_codex_outputs_materialization_plan(tmp_path: Path) -> None:
    _write_agent_config(tmp_path / ".comx-agent.toml")
    codex_home = tmp_path / "codex-home"
    _write_codex_contract(codex_home)

    result = CliRunner().invoke(
        app,
        [
            "agents",
            "plan-apply-codex",
            "--cwd",
            str(tmp_path),
            "--codex-home",
            str(codex_home),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["supported"] is True
    assert payload["target"] == "project"
    assert [file["agent_id"] for file in payload["files"]] == ["architect"]
    assert [file["materialized_agent_name"] for file in payload["files"]] == [
        "architect"
    ]


def test_agents_plan_apply_codex_can_target_global_namespace(tmp_path: Path) -> None:
    _write_agent_config(tmp_path / ".comx-agent.toml")
    codex_home = tmp_path / "codex-home"
    _write_codex_contract(codex_home)

    result = CliRunner().invoke(
        app,
        [
            "agents",
            "plan-apply-codex",
            "--cwd",
            str(tmp_path),
            "--codex-home",
            str(codex_home),
            "--target",
            "global",
            "--namespace",
            "sample-project",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["target"] == "global"
    assert payload["files"][0]["agent_id"] == "architect"
    assert payload["files"][0]["materialized_agent_name"] == "sample-project-architect"
    assert payload["files"][0]["target_path"] == str(
        codex_home / "agents" / "sample-project-architect.toml"
    )


def test_agents_apply_codex_dry_run_does_not_write(tmp_path: Path) -> None:
    _write_agent_config(tmp_path / ".comx-agent.toml")
    codex_home = tmp_path / "codex-home"
    _write_codex_contract(codex_home)

    result = CliRunner().invoke(
        app,
        [
            "agents",
            "apply-codex",
            "--cwd",
            str(tmp_path),
            "--codex-home",
            str(codex_home),
            "--dry-run",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["dry_run"] is True
    assert payload["plan"]["target"] == "project"
    assert payload["written_files"] == []
    assert not (tmp_path / ".codex" / "agents" / "architect.toml").exists()


def test_agents_codex_status_reports_generated_artifact_match(tmp_path: Path) -> None:
    _write_agent_config(tmp_path / ".comx-agent.toml")
    codex_home = tmp_path / "codex-home"
    _write_codex_contract(codex_home)

    apply_result = CliRunner().invoke(
        app,
        [
            "agents",
            "apply-codex",
            "--cwd",
            str(tmp_path),
            "--codex-home",
            str(codex_home),
            "--json",
        ],
    )
    status_result = CliRunner().invoke(
        app,
        [
            "agents",
            "codex-status",
            "--cwd",
            str(tmp_path),
            "--codex-home",
            str(codex_home),
            "--json",
        ],
    )

    assert apply_result.exit_code == 0
    assert status_result.exit_code == 0
    payload = orjson.loads(status_result.stdout)
    assert payload["up_to_date"] is True
    assert payload["target"] == "project"
    assert payload["files"][0]["matches"] is True
