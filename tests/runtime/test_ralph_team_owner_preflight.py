from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from omx_remote.cli import app
from omx_remote.runtime.ralph.ralph_control import build_ralph_team_launch_plan
from omx_remote.runtime.ralph.ralph_team_owner_preflight import (
    require_ralph_team_live_launch_owner_support,
)
from omx_remote.schemas.invoke.command_schemas import OmxCommandResult

runner = CliRunner()


def _write_valid_team_prd_artifact(tmp_path: Path) -> None:
    prd_dir = tmp_path / ".omx"
    prd_dir.mkdir(exist_ok=True)
    prd_payload = {
        "objective": "Ship owner-safe Team fanout",
        "scope": ["guard unsafe live Team launch"],
        "constraints": ["do not spawn workers when OMX ignores DAG owners"],
        "execution_plan": ["validate owner preservation before live launch"],
        "verification_expectations": ["live launch is blocked before omx team runs"],
        "requires_team_fanout": True,
        "team_worker_count": 2,
        "team_worker_assignments": [
            _team_assignment("worker-1", "Backend lane", "backend/api.py"),
            _team_assignment("worker-2", "Frontend lane", "frontend/App.tsx"),
        ],
        "team_admin": {
            "admin_id": "team-admin",
            "aggregation_policy": "collect_all_workers_then_review",
            "merge_policy": "review_before_merge",
            "completion_policy": "all_required_tasks_completed",
            "requires_human_for": ["merge conflicts or worker scope expansion"],
            "requires_llm_review_for": ["final aggregation report before Ralph review"],
            "final_report_required": True,
        },
        "continuation_policy": "review_required",
    }
    (prd_dir / "prd.json").write_text(json.dumps(prd_payload), encoding="utf-8")


def _team_assignment(worker_id: str, lane_name: str, owned_file: str) -> dict[str, object]:
    assignment = {
        "worker_id": worker_id,
        "lane_name": lane_name,
        "objective": f"Own {lane_name}",
        "owned_files": [owned_file],
        "read_only_context_files": ["README.md"],
        "forbidden_files": ["pyproject.toml"],
        "tdd_steps": ["Write failing regression", "Make regression pass"],
        "verification_commands": ["uv run pytest tests/runtime/test_ralph_team_owner_preflight.py -q"],
        "handoff_summary_required": "Summarize changed files and verification output.",
        "authorization_policy": "preapproved",
        "authorization_scope": {
            "allowed_commands": ["uv run pytest tests/runtime/test_ralph_team_owner_preflight.py -q"],
            "forbidden_commands": ["git push"],
            "requires_human_for": ["modify forbidden files"],
            "requires_llm_review_for": ["local checkpoint commit"],
        },
    }
    return assignment


def _write_supported_omx_dist(root: Path) -> None:
    team_dir = root / "team"
    team_dir.mkdir(parents=True)
    (team_dir / "dag-schema.d.ts").write_text(
        "export interface TeamDagNode { owner?: string; }",
        encoding="utf-8",
    )
    (team_dir / "dag-schema.js").write_text(
        "const parsed = { owner: asOptionalString(node.owner) };",
        encoding="utf-8",
    )
    (team_dir / "repo-aware-decomposition.js").write_text(
        "const allocationInput = [{ owner: node.owner }];",
        encoding="utf-8",
    )
    (team_dir / "allocation-policy.js").write_text(
        "const reason = 'preserves explicit DAG owner';",
        encoding="utf-8",
    )


def _write_unsupported_omx_dist(root: Path) -> None:
    team_dir = root / "team"
    team_dir.mkdir(parents=True)
    (team_dir / "dag-schema.d.ts").write_text(
        "export interface TeamDagNode { role?: string; }",
        encoding="utf-8",
    )
    (team_dir / "dag-schema.js").write_text(
        "const parsed = { role: asOptionalString(node.role) };",
        encoding="utf-8",
    )
    (team_dir / "repo-aware-decomposition.js").write_text(
        "const allocationInput = [{ role: node.role }];",
        encoding="utf-8",
    )
    (team_dir / "allocation-policy.js").write_text(
        "assignments.push({ ...task, owner: decision.owner });",
        encoding="utf-8",
    )


def test_ralph_team_live_launch_owner_preflight_accepts_supported_omx_dist(tmp_path: Path) -> None:
    omx_dist_root = tmp_path / "omx-dist"
    _write_supported_omx_dist(omx_dist_root)

    require_ralph_team_live_launch_owner_support(omx_dist_root=omx_dist_root)


def test_ralph_team_live_launch_owner_preflight_rejects_unsupported_omx_dist(tmp_path: Path) -> None:
    omx_dist_root = tmp_path / "omx-dist"
    _write_unsupported_omx_dist(omx_dist_root)

    with pytest.raises(
        ValueError,
        match=r"does not support preserving Team DAG node\.owner.*Unsupported markers:.*dag-schema.d.ts",
    ):
        require_ralph_team_live_launch_owner_support(omx_dist_root=omx_dist_root)


def test_ralph_team_live_launch_owner_preflight_reports_missing_explicit_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    missing_root = tmp_path / "missing-omx-dist"

    with pytest.raises(ValueError) as exc_info:
        require_ralph_team_live_launch_owner_support(omx_dist_root=missing_root)

    assert (
        "explicit `omx_dist_root` argument was provided but missing" in str(exc_info.value)
    )
    assert str(missing_root) in str(exc_info.value)


def test_ralph_team_live_launch_owner_preflight_reports_missing_env_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    missing_env_root = tmp_path / "missing-env-dist"
    monkeypatch.setenv("AGENT_REMOTE_OMX_DIST_ROOT", str(missing_env_root))
    monkeypatch.setenv("PATH", "")

    with pytest.raises(ValueError) as exc_info:
        require_ralph_team_live_launch_owner_support()

    assert (
        "AGENT_REMOTE_OMX_DIST_ROOT was set but path did not exist" in str(exc_info.value)
    )


def test_ralph_team_live_launch_owner_preflight_auto_detects_global_omx_from_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    omx_dist_root = tmp_path / "mock-omx" / "dist"
    _write_supported_omx_dist(omx_dist_root)
    (omx_dist_root / "cli").mkdir(parents=True)
    (omx_dist_root / "cli" / "omx.js").write_text("console.log('fake omx');", encoding="utf-8")

    fake_omx_bin_dir = tmp_path / "bin"
    fake_omx_bin_dir.mkdir()
    fake_omx_binary = fake_omx_bin_dir / "omx"
    fake_omx_binary.write_text(
        f"#!/usr/bin/env node\nrequire('{omx_dist_root / 'cli' / 'omx.js'}')\n",
        encoding="utf-8",
    )
    fake_omx_binary.chmod(0o755)

    current_path = os.environ.get("PATH", "")
    monkeypatch.setenv("PATH", f"{fake_omx_bin_dir}:{current_path}")
    monkeypatch.delenv("AGENT_REMOTE_OMX_DIST_ROOT", raising=False)

    require_ralph_team_live_launch_owner_support()


def test_build_ralph_team_launch_plan_blocks_live_owner_unsafe_runtime(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    omx_dist_root = tmp_path / "omx-dist"
    _write_unsupported_omx_dist(omx_dist_root)
    _write_valid_team_prd_artifact(tmp_path)

    with pytest.raises(ValueError, match=r"does not support preserving Team DAG node\.owner"):
        build_ralph_team_launch_plan(
            allow_non_tty=True,
            require_live_owner_preflight=True,
            omx_dist_root=omx_dist_root,
        )
    assert not (tmp_path / ".omx" / "plans").exists()


def test_ralph_launch_team_cli_blocks_live_launch_before_running_omx(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    omx_dist_root = tmp_path / "omx-dist"
    _write_unsupported_omx_dist(omx_dist_root)
    _write_valid_team_prd_artifact(tmp_path)
    monkeypatch.setenv("AGENT_REMOTE_OMX_DIST_ROOT", str(omx_dist_root))
    observed_commands: list[list[str]] = []

    def fake_run_omx_command(command: list[str], cwd: str | None = None) -> OmxCommandResult:
        observed_commands.append(command)
        return OmxCommandResult(exit_code=0, stdout="should-not-run", stderr="")

    monkeypatch.setattr("omx_remote.cli.run_omx_command", fake_run_omx_command)

    result = runner.invoke(app, ["ralph", "launch-team", "--allow-non-tty"])

    assert result.exit_code == 2
    assert "does not support preserving Team DAG node.owner" in result.stdout
    assert observed_commands == []
    assert not (tmp_path / ".omx" / "plans").exists()


def test_ralph_launch_team_plan_only_still_writes_owner_dag_when_runtime_is_unsupported(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    omx_dist_root = tmp_path / "omx-dist"
    _write_unsupported_omx_dist(omx_dist_root)
    _write_valid_team_prd_artifact(tmp_path)
    monkeypatch.setenv("AGENT_REMOTE_OMX_DIST_ROOT", str(omx_dist_root))

    result = runner.invoke(app, ["ralph", "launch-team", "--allow-non-tty", "--plan-only"])

    assert result.exit_code == 0
    assert '"planned_only": true' in result.stdout
    dag_path = next((tmp_path / ".omx" / "plans").glob("team-dag-*-ralph-team.json"))
    dag_payload = json.loads(dag_path.read_text(encoding="utf-8"))
    assert [node["owner"] for node in dag_payload["nodes"]] == ["worker-1", "worker-2"]
