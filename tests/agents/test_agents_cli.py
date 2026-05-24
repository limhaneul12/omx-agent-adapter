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
    _write_agent_config(tmp_path / ".agent-remote.toml")

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
    _write_agent_config(tmp_path / ".agent-remote.toml")

    result = CliRunner().invoke(
        app,
        ["agents", "list", "--cwd", str(tmp_path), "--enabled-only", "--json"],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert [agent["id"] for agent in payload["agents"]] == ["architect"]


def test_agents_list_human_output_marks_enabled_and_disabled(tmp_path: Path) -> None:
    _write_agent_config(tmp_path / ".agent-remote.toml")

    result = CliRunner().invoke(app, ["agents", "list", "--cwd", str(tmp_path)])

    assert result.exit_code == 0
    assert "architect" in result.stdout
    assert "enabled" in result.stdout
    assert "reviewer" in result.stdout
    assert "disabled" in result.stdout


def test_agents_show_outputs_one_agent_json(tmp_path: Path) -> None:
    _write_agent_config(tmp_path / ".agent-remote.toml")

    result = CliRunner().invoke(
        app,
        ["agents", "show", "architect", "--cwd", str(tmp_path), "--json"],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["agent"]["id"] == "architect"
    assert payload["agent"]["enabled"] is True


def test_agents_show_missing_agent_exits_nonzero(tmp_path: Path) -> None:
    _write_agent_config(tmp_path / ".agent-remote.toml")

    result = CliRunner().invoke(
        app,
        ["agents", "show", "missing", "--cwd", str(tmp_path), "--json"],
    )

    assert result.exit_code == 2
    payload = orjson.loads(result.stdout)
    assert "No agent named missing" in payload["error"]


def test_agents_validate_reports_valid_config(tmp_path: Path) -> None:
    _write_agent_config(tmp_path / ".agent-remote.toml")

    result = CliRunner().invoke(
        app,
        ["agents", "validate", "--cwd", str(tmp_path), "--json"],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["valid"] is True
    assert payload["agent_count"] == 2


def test_agents_validate_exits_nonzero_on_schema_error(tmp_path: Path) -> None:
    (tmp_path / ".agent-remote.toml").write_text(
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
