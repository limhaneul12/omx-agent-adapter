from __future__ import annotations

from importlib import import_module
from pathlib import Path


def _attr(module_name: str, attr_name: str) -> object:
    module = import_module(module_name)
    assert hasattr(module, attr_name), f"{module_name}.{attr_name} is required"
    return getattr(module, attr_name)


def test_mcp_execute_company_run_returns_actual_payload_and_run_id(
    monkeypatch,
    tmp_path: Path,
) -> None:
    tools_module = import_module(
        "omx_remote.runtime.mcp.omx_agent_company_run_payloads"
    )
    result_schema = _attr("omx_remote.schemas.company_run_schemas", "CompanyRunResult")

    def fake_execute_company_run(request):
        run_dir = tmp_path / ".comx-agent" / "runs" / "mcp-company-run"
        company_root = run_dir / "company-run"
        company_root.mkdir(parents=True)
        return result_schema.model_validate(  # type: ignore[attr-defined]
            {
                "run_id": "mcp-company-run",
                "command_id": "company-run",
                "qualified_id": "builtin:company-run",
                "cwd": str(tmp_path.resolve()),
                "dry_run": False,
                "status": "requires_agent_action",
                "run_dir": str(run_dir),
                "result_path": str(run_dir / "result.json"),
                "company_run_root": str(company_root),
                "blocked_reasons": [],
                "team_launch_attempted": False,
                "team_task": None,
                "artifacts": [str(company_root / "state.json")],
                "metadata": {},
            }
        )

    monkeypatch.setattr(tools_module, "execute_company_run", fake_execute_company_run)
    payload_builder = _attr(
        "omx_remote.runtime.mcp.omx_agent_company_run_payloads",
        "execute_company_run_tool_payload",
    )

    payload = payload_builder(  # type: ignore[operator]
        cwd=tmp_path,
        objective="run the full company loop",
        notes="no real Team in unit tests",
    )

    assert payload["ok"] is True
    assert payload["command_id"] == "company-run"
    assert payload["qualified_id"] == "builtin:company-run"
    assert payload["dry_run"] is False
    assert payload["status"] == "requires_agent_action"
    assert payload["run_id"] == "mcp-company-run"
    assert payload["company_run_root"].endswith("company-run")


def test_mcp_status_and_artifacts_payloads_read_company_run_record(
    monkeypatch,
    tmp_path: Path,
) -> None:
    status_payload = _attr(
        "omx_remote.runtime.mcp.omx_agent_company_run_payloads",
        "company_run_status_tool_payload",
    )
    artifacts_payload = _attr(
        "omx_remote.runtime.mcp.omx_agent_company_run_payloads",
        "company_run_artifacts_tool_payload",
    )
    engine_class = _attr("omx_remote.runtime.company_run.engine", "CompanyRunEngine")
    request_schema = _attr(
        "omx_remote.schemas.company_run_schemas",
        "CompanyRunExecutionRequest",
    )
    request = request_schema.model_validate(  # type: ignore[attr-defined]
        {
            "objective": "read a fully typed company-run record",
            "cwd": str(tmp_path),
            "autonomy": "agent",
            "council_mode": "artifact",
            "live_team_allowed": False,
        }
    )
    result_record = engine_class(team_launcher=lambda _request: None).execute(request)  # type: ignore[operator]

    status = status_payload(cwd=tmp_path, run_id=result_record.run_id)  # type: ignore[operator]
    artifacts = artifacts_payload(cwd=tmp_path, run_id=result_record.run_id)  # type: ignore[operator]

    assert status["ok"] is True
    assert status["run_id"] == result_record.run_id
    assert status["status"] == "requires_agent_action"
    assert status["current_phase"] == "memory_closeout"
    assert artifacts["ok"] is True
    assert "company-run/state.json" in "\n".join(artifacts["artifact_paths"])
    assert (
        artifacts["artifacts"]["company-run/state.json"]["run_id"]
        == result_record.run_id
    )


def test_mcp_artifacts_payload_rejects_symlink_escape(tmp_path: Path) -> None:
    artifacts_payload = _attr(
        "omx_remote.runtime.mcp.omx_agent_company_run_payloads",
        "company_run_artifacts_tool_payload",
    )
    run_dir = tmp_path / ".comx-agent" / "runs" / "symlink-company-run"
    company_root = run_dir / "company-run"
    company_root.mkdir(parents=True)
    external_file = tmp_path / "outside-secret.txt"
    external_file.write_text("do not expose", encoding="utf-8")
    (company_root / "hostlink.txt").symlink_to(external_file)
    (company_root / "artifact-index.json").write_text(
        """
{
  "run_id": "symlink-company-run",
  "root_path": "COMPANY_ROOT",
  "artifact_paths": ["HOST_LINK"],
  "artifacts": []
}
""".replace("COMPANY_ROOT", str(company_root)).replace(
            "HOST_LINK", str(company_root / "hostlink.txt")
        ),
        encoding="utf-8",
    )

    artifacts = artifacts_payload(cwd=tmp_path, run_id="symlink-company-run")  # type: ignore[operator]

    assert artifacts["ok"] is True
    assert "do not expose" not in str(artifacts["artifacts"])
    assert str(company_root / "hostlink.txt") in artifacts["unsafe_artifact_paths"]
