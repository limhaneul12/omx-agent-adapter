from collections.abc import Callable
from pathlib import Path

from omx_remote.runtime.commands.artifacts.actual_run_record_writer import (
    ActualRunPaths,
)
from omx_remote.runtime.company_run.artifacts.artifact_writers import (
    ensure_company_run_tree,
    write_artifact_index,
    write_company_json,
    write_company_state,
)
from omx_remote.runtime.company_run.artifacts.result_persistence import (
    actual_company_run_paths,
    alexandria_tool_points,
    blocked_reasons_from_team,
    company_run_artifact_records,
    final_status_from_team,
    write_final_company_run_files,
    write_initial_company_run_files,
)
from omx_remote.runtime.company_run.governance.roster_policy import (
    default_company_run_roster,
    validate_company_run_roster,
    validate_vote_authorship,
)
from omx_remote.runtime.company_run.phases.phase_sequence import (
    CompanyRunPhaseSequence,
)
from omx_remote.runtime.company_run.team.team_runtime import build_team_task
from omx_remote.runtime.runs.run_artifact_store import allocate_unique_run_dir
from omx_remote.schemas.company_run_gate_schemas import CompanyRunDiscoveryArtifacts
from omx_remote.schemas.company_run_schemas import (
    CompanyRunExecutionRequest,
    CompanyRunPhaseRecord,
    CompanyRunResult,
    CompanyRunResultMetadata,
    CompanyRunRoster,
    CompanyRunState,
    CompanyRunTeamRequest,
    CompanyRunVoteRecord,
)
from omx_remote.shared.omx_enums.company_run_enums import (
    CompanyRunFinalStatus,
    CompanyRunPhase,
)
from omx_remote.shared.omx_enums.discovery_gate_enums import DiscoveryGateVerdict
from omx_remote.shared.utils.runtime_identity import utc_compact_timestamp

TeamLauncher = Callable[[CompanyRunTeamRequest], object]


class CompanyRunEngine:
    """Execute the real company-run lifecycle with typed gates and artifacts."""

    def __init__(self, team_launcher: TeamLauncher | None = None) -> None:
        """Create a company-run engine.

        Args:
            team_launcher [TeamLauncher | None]: Optional injected Team launcher.
        """
        self._phase_sequence = CompanyRunPhaseSequence(team_launcher=team_launcher)
        self._team_launcher = team_launcher

    def execute(self, request: CompanyRunExecutionRequest) -> CompanyRunResult:
        """Execute one company-run request.

        Args:
            request [CompanyRunExecutionRequest]: Actual execution request.

        Returns:
            CompanyRunResult: MCP/CLI-friendly result.
        """
        cwd = Path(request.cwd).expanduser().resolve()
        run_id, run_dir = allocate_unique_run_dir(
            cwd,
            utc_compact_timestamp(),
            "company-run",
        )
        company_root = run_dir / "company-run"
        ensure_company_run_tree(company_root)
        paths = actual_company_run_paths(run_id, run_dir)
        write_initial_company_run_files(paths, request)

        roster = default_company_run_roster(str(company_root))
        validate_company_run_roster(roster)
        write_company_json(company_root / "roster.json", roster)

        phase_records: list[CompanyRunPhaseRecord] = []
        vote_records: list[CompanyRunVoteRecord] = []
        council_mode = str(request.council_mode)
        live_team_allowed = request.live_team_allowed

        discovery_artifacts = self._phase_sequence.write_memory_and_route_artifacts(
            company_root=company_root,
            request=request,
            phase_records=phase_records,
        )
        if not discovery_artifacts.should_continue:
            result = self._finalize_after_discovery_stop(
                paths=paths,
                request=request,
                run_id=run_id,
                run_dir=run_dir,
                company_root=company_root,
                cwd=cwd,
                roster=roster,
                phase_records=phase_records,
                discovery_artifacts=discovery_artifacts,
            )
            return result
        council_results = self._phase_sequence.run_research_council(
            paths=paths,
            cwd=cwd,
            company_root=company_root,
            request=request,
            roster=roster,
            phase_records=phase_records,
            council_mode=council_mode,
        )
        council_failures = tuple(
            result.failure.reason
            for result in council_results
            if result.failure is not None
        )
        if council_failures:
            records = company_run_artifact_records(company_root)
            state = CompanyRunState(
                run_id=run_id,
                objective=request.objective,
                cwd=str(cwd),
                runtime_options=request.runtime_options,
                status=CompanyRunFinalStatus.BLOCKED,
                current_phase=CompanyRunPhase.RESEARCH_BRIEF_LOOP,
                roster=roster,
                phases=tuple(phase_records),
                votes=(),
                artifacts=records,
                team_launch=None,
                alexandria_tool_points=alexandria_tool_points(),
                blocked_reasons=council_failures,
            )
            state_path = write_company_state(company_root, state)
            records = company_run_artifact_records(company_root)
            state = state.model_copy(update={"artifacts": records})
            state_path = write_company_state(company_root, state)
            artifact_index_path = write_artifact_index(company_root, run_id, records)
            result = CompanyRunResult(
                run_id=run_id,
                command_id="company-run",
                qualified_id="builtin:company-run",
                cwd=str(cwd),
                dry_run=False,
                status=CompanyRunFinalStatus.BLOCKED.value,
                run_dir=str(run_dir),
                result_path=str(paths.result_path),
                company_run_root=str(company_root),
                blocked_reasons=council_failures,
                team_launch_attempted=False,
                team_task=build_team_task(
                    objective=request.objective,
                    company_root=company_root,
                    worker_count=request.worker_count,
                    runtime_options=request.runtime_options,
                ),
                runtime_options=request.runtime_options,
                artifacts=tuple(record.path for record in records),
                metadata=CompanyRunResultMetadata(
                    state_path=str(state_path),
                    artifact_index_path=str(artifact_index_path),
                ),
            )
            write_final_company_run_files(paths, result, artifact_index_path)
            return result
        self._phase_sequence.write_research_vote(
            company_root=company_root,
            roster=roster,
            phase_records=phase_records,
            vote_records=vote_records,
        )
        self._phase_sequence.write_proceed_vote(
            company_root=company_root,
            roster=roster,
            phase_records=phase_records,
            vote_records=vote_records,
        )
        self._phase_sequence.write_planning_artifacts(
            company_root=company_root,
            request=request,
            phase_records=phase_records,
        )
        self._phase_sequence.write_executive_gate(
            company_root=company_root,
            roster=roster,
            phase_records=phase_records,
            vote_records=vote_records,
        )
        self._phase_sequence.write_implementation_kickoff(
            company_root=company_root,
            request=request,
            phase_records=phase_records,
        )
        validate_vote_authorship(votes=tuple(vote_records))
        team_record = self._phase_sequence.run_team_gate(
            paths=paths,
            cwd=cwd,
            company_root=company_root,
            request=request,
            live_team_allowed=live_team_allowed,
            phase_records=phase_records,
        )
        self._phase_sequence.write_post_team_gates(
            company_root=company_root,
            phase_records=phase_records,
            team_status=team_record.status,
        )

        final_status = final_status_from_team(team_record.status)
        blocked_reasons = blocked_reasons_from_team(team_record.status)
        initial_records = company_run_artifact_records(company_root)
        state = CompanyRunState(
            run_id=run_id,
            objective=request.objective,
            cwd=str(cwd),
            runtime_options=request.runtime_options,
            status=final_status,
            current_phase=CompanyRunPhase.MEMORY_CLOSEOUT,
            roster=roster,
            phases=tuple(phase_records),
            votes=tuple(vote_records),
            artifacts=initial_records,
            team_launch=team_record,
            alexandria_tool_points=alexandria_tool_points(),
            blocked_reasons=blocked_reasons,
        )
        state_path = write_company_state(company_root, state)
        records = company_run_artifact_records(company_root)
        if records != initial_records:
            state = state.model_copy(update={"artifacts": records})
            state_path = write_company_state(company_root, state)
        artifact_index_path = write_artifact_index(company_root, run_id, records)
        result = CompanyRunResult(
            run_id=run_id,
            command_id="company-run",
            qualified_id="builtin:company-run",
            cwd=str(cwd),
            dry_run=False,
            status=final_status.value,
            run_dir=str(run_dir),
            result_path=str(paths.result_path),
            company_run_root=str(company_root),
            blocked_reasons=blocked_reasons,
            team_launch_attempted=live_team_allowed or self._team_launcher is not None,
            team_task=build_team_task(
                objective=request.objective,
                company_root=company_root,
                worker_count=request.worker_count,
                runtime_options=request.runtime_options,
            ),
            runtime_options=request.runtime_options,
            artifacts=tuple(record.path for record in records),
            metadata=CompanyRunResultMetadata(
                state_path=str(state_path),
                artifact_index_path=str(artifact_index_path),
            ),
        )
        write_final_company_run_files(paths, result, artifact_index_path)
        return result

    def _finalize_after_discovery_stop(
        self,
        paths: ActualRunPaths,
        request: CompanyRunExecutionRequest,
        run_id: str,
        run_dir: Path,
        company_root: Path,
        cwd: Path,
        roster: CompanyRunRoster,
        phase_records: list[CompanyRunPhaseRecord],
        discovery_artifacts: CompanyRunDiscoveryArtifacts,
    ) -> CompanyRunResult:
        """Finalize a run stopped by company-run Gate 0.

        Args:
            paths: Actual-run artifact paths.
            request [CompanyRunExecutionRequest]: Company-run request.
            run_id [str]: Run id.
            run_dir [Path]: Run directory.
            company_root [Path]: Company-run artifact root.
            cwd [Path]: Resolved repository root.
            roster: Validated company-run roster.
            phase_records [list[CompanyRunPhaseRecord]]: Phase log.
            discovery_artifacts [CompanyRunDiscoveryArtifacts]: Gate 0 artifacts.

        Returns:
            CompanyRunResult: Final result without Team launch.
        """
        blocked_reasons = (
            (discovery_artifacts.stop_reason,)
            if discovery_artifacts.stop_reason is not None
            else ()
        )
        final_status = _final_status_from_discovery_verdict(
            verdict=DiscoveryGateVerdict(discovery_artifacts.verdict)
        )
        initial_records = company_run_artifact_records(company_root)
        state = CompanyRunState(
            run_id=run_id,
            objective=request.objective,
            cwd=str(cwd),
            runtime_options=request.runtime_options,
            status=final_status,
            current_phase=CompanyRunPhase.DISCOVERY_GATE,
            roster=roster,
            phases=tuple(phase_records),
            votes=(),
            artifacts=initial_records,
            team_launch=None,
            alexandria_tool_points=alexandria_tool_points(),
            blocked_reasons=blocked_reasons,
        )
        state_path = write_company_state(company_root, state)
        records = company_run_artifact_records(company_root)
        if records != initial_records:
            state = state.model_copy(update={"artifacts": records})
            state_path = write_company_state(company_root, state)
        artifact_index_path = write_artifact_index(company_root, run_id, records)
        result = CompanyRunResult(
            run_id=run_id,
            command_id="company-run",
            qualified_id="builtin:company-run",
            cwd=str(cwd),
            dry_run=False,
            status=final_status.value,
            run_dir=str(run_dir),
            result_path=str(paths.result_path),
            company_run_root=str(company_root),
            blocked_reasons=blocked_reasons,
            team_launch_attempted=False,
            team_task=None,
            runtime_options=request.runtime_options,
            artifacts=tuple(record.path for record in records),
            metadata=CompanyRunResultMetadata(
                state_path=str(state_path),
                artifact_index_path=str(artifact_index_path),
                discovery_decision_report_path=(
                    discovery_artifacts.decision_report_markdown_path
                ),
            ),
        )
        write_final_company_run_files(paths, result, artifact_index_path)
        return result


def execute_company_run(request: CompanyRunExecutionRequest) -> CompanyRunResult:
    """Execute one company-run request with the default engine.

    Args:
        request [CompanyRunExecutionRequest]: Execution request.

    Returns:
        CompanyRunResult: Actual company-run result.
    """
    engine = CompanyRunEngine()
    result = engine.execute(request)
    return result


def _final_status_from_discovery_verdict(
    verdict: DiscoveryGateVerdict,
) -> CompanyRunFinalStatus:
    """Map Gate 0 verdict to final company-run status.

    Args:
        verdict [DiscoveryGateVerdict]: Gate 0 verdict.

    Returns:
        CompanyRunFinalStatus: Final status for stopped runs.
    """
    if verdict == DiscoveryGateVerdict.NO_BUILD:
        return CompanyRunFinalStatus.SUCCEEDED
    if verdict == DiscoveryGateVerdict.BLOCKED:
        return CompanyRunFinalStatus.BLOCKED
    return CompanyRunFinalStatus.REQUIRES_AGENT_ACTION


__all__ = [
    "CompanyRunEngine",
    "execute_company_run",
]
