from __future__ import annotations

from pathlib import Path

import orjson
from comx_harness.cli import app
from typer.testing import CliRunner

runner = CliRunner()
REPOSITORY_ROOT = Path(__file__).parents[3]
DOGFOOD_SPEC_PATH = (
    REPOSITORY_ROOT / "examples" / "codex-subagents" / "stock-informer.json"
)


def test_codex_subagent_validate_register_and_list_emit_json(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    validation_result = runner.invoke(
        app,
        [
            "agent",
            "codex-subagents",
            "validate",
            str(workspace),
            str(DOGFOOD_SPEC_PATH),
        ],
    )
    assert validation_result.exit_code == 0
    validation = orjson.loads(validation_result.stdout)
    assert validation["valid"] is True
    assert validation["mutation_performed"] is False
    assert not (workspace / ".codex").exists()

    registration_result = runner.invoke(
        app,
        [
            "agent",
            "codex-subagents",
            "register",
            str(workspace),
            str(DOGFOOD_SPEC_PATH),
        ],
    )
    assert registration_result.exit_code == 0
    registration = orjson.loads(registration_result.stdout)
    assert registration["registry"]["valid"] is True
    assert len(registration["written_files"]) == 6

    list_result = runner.invoke(
        app,
        ["agent", "codex-subagents", "list", str(workspace)],
    )
    assert list_result.exit_code == 0
    state = orjson.loads(list_result.stdout)
    assert state["valid"] is True
    assert state["max_concurrent_threads_per_session"] == 5
    assert len(state["agents"]) == 5


def test_codex_subagent_cli_rejects_invalid_name_as_json_error(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    invalid_spec = tmp_path / "invalid.json"
    invalid_spec.write_bytes(
        orjson.dumps(
            {
                "schema_version": "codex-subagent-registration.v1",
                "agents": [
                    {
                        "name": "../escape",
                        "description": "Invalid",
                        "developer_instructions": "Do not run.",
                        "model": "gpt-5.6-luna",
                        "model_reasoning_effort": "max",
                        "sandbox_mode": "read-only",
                    }
                ],
            }
        )
    )

    result = runner.invoke(
        app,
        [
            "agent",
            "codex-subagents",
            "validate",
            str(workspace),
            str(invalid_spec),
        ],
    )

    assert result.exit_code == 2
    payload = orjson.loads(result.stderr)
    assert payload["status"] == "error"
    assert payload["code"] == "validation_error"
    assert not (workspace / ".codex").exists()


def test_codex_subagent_cli_rejects_user_home_workspace() -> None:
    result = runner.invoke(
        app,
        [
            "agent",
            "codex-subagents",
            "validate",
            str(Path.home()),
            str(DOGFOOD_SPEC_PATH),
        ],
    )

    assert result.exit_code == 2
    payload = orjson.loads(result.stderr)
    assert payload["status"] == "error"
    assert payload["code"] == "operation_failed"
    assert "User home" in payload["message"]


def test_codex_subagent_cli_rejects_user_global_codex_workspace() -> None:
    result = runner.invoke(
        app,
        [
            "agent",
            "codex-subagents",
            "validate",
            str(Path.home() / ".codex"),
            str(DOGFOOD_SPEC_PATH),
        ],
    )

    assert result.exit_code == 2
    payload = orjson.loads(result.stderr)
    assert payload["status"] == "error"
    assert payload["code"] == "operation_failed"
    assert "user-global Codex directory" in payload["message"]


def test_codex_subagent_cli_rejects_user_global_codex_alias(
    tmp_path: Path,
) -> None:
    codex_alias = tmp_path / "codex-alias"
    codex_alias.symlink_to(Path.home() / ".codex", target_is_directory=True)

    result = runner.invoke(
        app,
        [
            "agent",
            "codex-subagents",
            "validate",
            str(codex_alias),
            str(DOGFOOD_SPEC_PATH),
        ],
    )

    assert result.exit_code == 2
    payload = orjson.loads(result.stderr)
    assert payload["status"] == "error"
    assert payload["code"] == "operation_failed"
    assert "user-global Codex directory" in payload["message"]
