from __future__ import annotations

import subprocess
from pathlib import Path

import orjson
from comx_harness.cli import app
from typer.testing import CliRunner

runner = CliRunner()


def _git(path: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ("git", "-C", str(path), *arguments),
        check=True,
        capture_output=True,
        text=True,
    )


def _repository(path: Path) -> Path:
    path.mkdir()
    _git(path, "init", "-b", "main")
    _git(path, "config", "user.email", "tests@example.com")
    _git(path, "config", "user.name", "Test User")
    (path / "README.md").write_text("initial\n", encoding="utf-8")
    _git(path, "add", "README.md")
    _git(path, "commit", "-m", "initial")
    return path


def test_agent_register_and_context_are_machine_readable(
    tmp_path: Path,
    fake_provider_path: Path,
) -> None:
    repository = _repository(tmp_path / "repository")
    state_root = tmp_path / "state"

    registration_result = runner.invoke(
        app,
        [
            "agent",
            "register-project",
            str(repository),
            "--state-root",
            str(state_root),
        ],
    )
    assert registration_result.exit_code == 0
    registration = orjson.loads(registration_result.stdout)

    context_result = runner.invoke(
        app,
        [
            "agent",
            "context",
            "--state-root",
            str(state_root),
        ],
    )
    assert context_result.exit_code == 0
    context = orjson.loads(context_result.stdout)

    assert registration["project"]["root_path"] == str(repository.resolve())
    assert registration["workspace"]["root_path"] == str(repository.resolve())
    assert (
        context["catalog"]["projects"][0]["project_id"]
        == registration["project"]["project_id"]
    )
    assert (
        context["catalog"]["workspaces"][0]["workspace_id"]
        == registration["workspace"]["workspace_id"]
    )
    assert {item["provider"] for item in context["capabilities"]["providers"]} == {
        "codex",
        "omx",
    }
    assert context["attention_count"] == 0


def test_agent_unknown_workspace_returns_structured_error(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "agent",
            "inspect-workspace",
            "missing",
            "--state-root",
            str(tmp_path / "state"),
        ],
    )

    assert result.exit_code == 2
    payload = orjson.loads(result.stderr)
    assert payload["status"] == "error"
    assert payload["code"] == "not_found"


def test_agent_starts_and_tracks_detached_run_operation(
    tmp_path: Path,
    fake_provider_path: Path,
) -> None:
    del fake_provider_path
    import time

    from comx_harness.schemas.ade_inspection_schemas import DetachedOperationRequest
    from comx_harness.schemas.execution_schemas import ExecutionRequest
    from comx_harness.shared.harness_enums.provider_enums import ProviderId

    state_root = tmp_path / "state"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    request_path = tmp_path / "operation-request.json"
    request_path.write_text(
        DetachedOperationRequest(
            operation="run",
            request=ExecutionRequest(
                provider=ProviderId.CODEX,
                objective="Complete as a detached agent operation",
                workspace=str(workspace),
                idempotency_key="agent-detached-01",
            ),
        ).model_dump_json(indent=2),
        encoding="utf-8",
    )

    launched_result = runner.invoke(
        app,
        [
            "agent",
            "start-operation",
            str(request_path),
            "--state-root",
            str(state_root),
        ],
    )
    assert launched_result.exit_code == 0
    launched = orjson.loads(launched_result.stdout)
    assert launched["status"] == "running"

    deadline = time.monotonic() + 10.0
    current = launched
    while current["status"] == "running" and time.monotonic() < deadline:
        time.sleep(0.05)
        current_result = runner.invoke(
            app,
            [
                "agent",
                "operation",
                launched["operation_id"],
                "--state-root",
                str(state_root),
            ],
        )
        assert current_result.exit_code == 0
        current = orjson.loads(current_result.stdout)

    assert current["status"] == "succeeded"

    list_result = runner.invoke(
        app,
        ["agent", "operations", "--state-root", str(state_root)],
    )
    assert list_result.exit_code == 0
    collection = orjson.loads(list_result.stdout)
    assert collection["operations"][0]["operation_id"] == launched["operation_id"]

    context_result = runner.invoke(
        app,
        ["agent", "context", "--state-root", str(state_root)],
    )
    assert context_result.exit_code == 0
    context = orjson.loads(context_result.stdout)
    assert context["operations"][0]["status"] == "succeeded"
