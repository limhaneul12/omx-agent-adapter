from pathlib import Path

from omx_remote.runtime.company_run.engine import CompanyRunEngine
from omx_remote.schemas.company_run.company_run_runtime_schemas import CompanyRunExecutionRequest
from omx_remote.shared.omx_enums.company_run_enums import CompanyRunCouncilMode


def test_company_run_vague_objective_stops_for_deep_interview(tmp_path: Path) -> None:
    launched_requests: list[object] = []
    request = CompanyRunExecutionRequest(
        objective="vague unclear company-run idea with missing non-goals",
        cwd=str(tmp_path),
        autonomy="agent",
        council_mode=CompanyRunCouncilMode.ARTIFACT,
        live_team_allowed=False,
    )
    engine = CompanyRunEngine(team_launcher=launched_requests.append)

    result = engine.execute(request=request)

    company_root = Path(result.company_run_root)
    assert result.status == "requires_agent_action"
    assert result.team_launch_attempted is False
    assert result.team_task is None
    assert launched_requests == []
    assert (company_root / "discovery" / "deep-interview-handoff.md").exists()
    assert (company_root / "decisions" / "discovery-decision-report.md").exists()
    assert any("deep-interview" in reason for reason in result.blocked_reasons)


def test_company_run_no_build_stops_before_research_and_team(tmp_path: Path) -> None:
    launched_requests: list[object] = []
    request = CompanyRunExecutionRequest(
        objective="no-build this duplicated workflow",
        cwd=str(tmp_path),
        autonomy="agent",
        council_mode=CompanyRunCouncilMode.ARTIFACT,
        live_team_allowed=False,
    )
    engine = CompanyRunEngine(team_launcher=launched_requests.append)

    result = engine.execute(request=request)

    company_root = Path(result.company_run_root)
    assert result.status == "succeeded"
    assert result.team_launch_attempted is False
    assert result.team_task is None
    assert launched_requests == []
    assert not (company_root / "research" / "research-vote.json").exists()
    assert (company_root / "discovery" / "roi-no-build-gate.json").exists()
