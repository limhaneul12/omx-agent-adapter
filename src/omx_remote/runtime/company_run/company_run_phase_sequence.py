from pathlib import Path

from omx_remote.runtime.commands.artifacts.actual_run_record_writer import (
    ActualRunPaths,
)
from omx_remote.runtime.company_run.company_run_artifacts import (
    artifact_record,
    write_company_json,
    write_company_markdown,
)
from omx_remote.runtime.company_run.company_run_council_runtime import (
    CouncilLaneRequest,
    CouncilRunResult,
    run_council_subagents,
)
from omx_remote.runtime.company_run.company_run_discovery_phase import (
    write_company_run_discovery_artifacts,
)
from omx_remote.runtime.company_run.company_run_governance_phase import (
    write_company_run_executive_gate,
    write_company_run_implementation_kickoff,
    write_company_run_planning_artifacts,
    write_company_run_proceed_vote,
    write_company_run_research_vote,
)
from omx_remote.runtime.company_run.company_run_phase_log import (
    append_company_run_phase,
)
from omx_remote.runtime.company_run.company_run_phase_texts import (
    memory_recall_markdown,
)
from omx_remote.runtime.company_run.company_run_team_phase import (
    run_team_gate_for_company_run,
    write_post_team_gates_for_company_run,
)
from omx_remote.schemas.company_run_gate_schemas import CompanyRunDiscoveryArtifacts
from omx_remote.schemas.company_run_schemas import (
    CompanyRunExecutionRequest,
    CompanyRunPhaseRecord,
    CompanyRunRoster,
    CompanyRunRouteNextArtifactPayload,
    CompanyRunTeamLaunchRecord,
    CompanyRunVoteRecord,
)
from omx_remote.shared.omx_enums.company_run_enums import (
    CompanyRunArtifactKind,
    CompanyRunPhase,
    CompanyRunPhaseStatus,
    CompanyRunRoleGroup,
    CompanyRunTeamLaunchStatus,
)


class CompanyRunPhaseSequence:
    """Write ordered company-run phase artifacts and gate decisions."""

    def __init__(self, team_launcher=None) -> None:
        """Initialize with injected Team launcher. Args: team_launcher: Optional Team hook."""
        self._team_launcher = team_launcher

    def write_memory_recall_artifact(
        self,
        company_root: Path,
        request: CompanyRunExecutionRequest,
        phase_records: list[CompanyRunPhaseRecord],
    ) -> None:
        """Write Gate -1 memory artifact. Args: company_root: Root; request: Request; phase_records: Log."""
        memory_path = company_root / "memory-recall.md"
        write_company_markdown(
            path=memory_path,
            text=memory_recall_markdown(request.objective),
        )
        append_company_run_phase(
            phase_records,
            CompanyRunPhase.MEMORY_RECALL,
            "Alexandria MCP memory recall points recorded.",
            (artifact_record(CompanyRunArtifactKind.MEMORY, memory_path),),
        )

    def write_discovery_gate_artifacts(
        self,
        company_root: Path,
        request: CompanyRunExecutionRequest,
        phase_records: list[CompanyRunPhaseRecord],
    ) -> CompanyRunDiscoveryArtifacts:
        """Write Gate 0 artifacts. Args: company_root: Root; request: Request; phase_records: Log. Returns: CompanyRunDiscoveryArtifacts: Paths and verdict."""
        discovery_artifacts = write_company_run_discovery_artifacts(
            company_root=company_root,
            request=request,
        )
        artifact_records = (
            artifact_record(
                CompanyRunArtifactKind.DISCOVERY,
                Path(discovery_artifacts.discovery_decision_packet_path),
            ),
            artifact_record(
                CompanyRunArtifactKind.DISCOVERY,
                Path(discovery_artifacts.discovery_summary_path),
            ),
            artifact_record(
                CompanyRunArtifactKind.DISCOVERY,
                Path(discovery_artifacts.roi_no_build_gate_path),
            ),
            artifact_record(
                CompanyRunArtifactKind.DISCOVERY,
                Path(discovery_artifacts.deep_interview_handoff_path),
            ),
            artifact_record(
                CompanyRunArtifactKind.DECISION_REPORT,
                Path(discovery_artifacts.decision_report_markdown_path),
            ),
        )
        blocked_reasons = (
            (discovery_artifacts.stop_reason,)
            if discovery_artifacts.stop_reason is not None
            else ()
        )
        append_company_run_phase(
            phase_records,
            CompanyRunPhase.DISCOVERY_GATE,
            _discovery_gate_phase_summary(
                should_continue=discovery_artifacts.should_continue
            ),
            artifact_records,
            status=_discovery_gate_phase_status(
                should_continue=discovery_artifacts.should_continue
            ),
            blocked_reasons=blocked_reasons,
        )
        return discovery_artifacts

    def write_route_next_artifact(
        self,
        company_root: Path,
        request: CompanyRunExecutionRequest,
        phase_records: list[CompanyRunPhaseRecord],
    ) -> None:
        """Write route-next artifact. Args: company_root: Root; request: Request; phase_records: Log."""
        route_path = company_root / "route-next.json"
        route_payload = CompanyRunRouteNextArtifactPayload(
            route="company-run",
            team_required=True,
            subagents_required=True,
            one_agent_show_allowed=False,
            objective=request.objective,
        )
        write_company_json(path=route_path, payload=route_payload)
        append_company_run_phase(
            phase_records,
            CompanyRunPhase.ROUTE_NEXT,
            "route-next gate selected company-run with Team/subagent requirements.",
            (artifact_record(CompanyRunArtifactKind.STATE, route_path),),
        )

    def write_memory_and_route_artifacts(
        self,
        company_root: Path,
        request: CompanyRunExecutionRequest,
        phase_records: list[CompanyRunPhaseRecord],
    ) -> CompanyRunDiscoveryArtifacts:
        """Write front gates. Args: company_root: Root; request: Request; phase_records: Log. Returns: CompanyRunDiscoveryArtifacts: Paths and verdict."""
        self.write_memory_recall_artifact(
            company_root=company_root,
            request=request,
            phase_records=phase_records,
        )
        discovery_artifacts = self.write_discovery_gate_artifacts(
            company_root=company_root,
            request=request,
            phase_records=phase_records,
        )
        if discovery_artifacts.should_continue:
            self.write_route_next_artifact(
                company_root=company_root,
                request=request,
                phase_records=phase_records,
            )
        return discovery_artifacts

    def run_research_council(
        self,
        paths: ActualRunPaths,
        cwd: Path,
        company_root: Path,
        request: CompanyRunExecutionRequest,
        roster: CompanyRunRoster,
        phase_records: list[CompanyRunPhaseRecord],
        council_mode: str,
    ) -> tuple[CouncilRunResult, ...]:
        """Run independent research council lanes and record artifacts.

        Args:
            paths [ActualRunPaths]: Actual-run artifact paths.
            cwd [Path]: Repository root under orchestration.
            company_root [Path]: Company-run artifact root.
            request [CompanyRunExecutionRequest]: Execution request.
            roster [CompanyRunRoster]: Validated company-run roster.
            phase_records [list[CompanyRunPhaseRecord]]: Mutable phase log records.
            council_mode [str]: Council execution mode.

        Returns:
            tuple[CouncilRunResult, ...]: Council lane execution results.
        """
        research_specs = (
            (
                "market/domain researcher",
                "research/domain-research.md",
                "Domain Research",
                ("problem/domain evidence", "alternatives", "build/no-build signals"),
            ),
            (
                "technical feasibility researcher",
                "research/technical-feasibility.md",
                "Technical Feasibility",
                (
                    "architecture feasibility",
                    "dependencies",
                    "implementation constraints",
                ),
            ),
            (
                "risk/security researcher",
                "research/risk-security.md",
                "Risk and Security Research",
                ("security", "privacy", "maintenance", "operational risk"),
            ),
            (
                "critic",
                "research/critic.md",
                "Research Critic",
                ("hidden assumptions", "no-build case", "remaining ambiguity"),
            ),
        )
        research_seats = roster.seats_for_group(CompanyRunRoleGroup.RESEARCH)
        council_requests = tuple(
            CouncilLaneRequest(
                paths=paths,
                cwd=cwd,
                agent_name=research_seats[
                    min(attempt_number - 1, len(research_seats) - 1)
                ].agent,
                role=role,
                objective=request.objective,
                artifact_label=label,
                required_points=points,
                output_path=company_root / relative_path,
                timeout_seconds=request.timeout_seconds,
                step_index=1,
                attempt_number=attempt_number,
                mode=council_mode,
                runtime_options=request.runtime_options,
            )
            for attempt_number, (role, relative_path, label, points) in enumerate(
                research_specs,
                start=1,
            )
        )
        council_results = run_council_subagents(requests=council_requests)
        artifacts = tuple(
            artifact_record(CompanyRunArtifactKind.RESEARCH, company_root / relative)
            for _, relative, _, _ in research_specs
        )
        append_company_run_phase(
            phase_records,
            CompanyRunPhase.RESEARCH_BRIEF_LOOP,
            "Independent research council lanes completed.",
            artifacts,
        )
        return council_results

    def write_research_vote(
        self,
        company_root: Path,
        roster: CompanyRunRoster,
        phase_records: list[CompanyRunPhaseRecord],
        vote_records: list[CompanyRunVoteRecord],
    ) -> None:
        """Write research decision. Args: company_root: Root; roster: Roster; phase_records: Log; vote_records: Votes."""
        write_company_run_research_vote(
            company_root=company_root,
            roster=roster,
            phase_records=phase_records,
            vote_records=vote_records,
        )

    def write_proceed_vote(
        self,
        company_root: Path,
        roster: CompanyRunRoster,
        phase_records: list[CompanyRunPhaseRecord],
        vote_records: list[CompanyRunVoteRecord],
    ) -> None:
        """Write proceed decision. Args: company_root: Root; roster: Roster; phase_records: Log; vote_records: Votes."""
        write_company_run_proceed_vote(
            company_root=company_root,
            roster=roster,
            phase_records=phase_records,
            vote_records=vote_records,
        )

    def write_planning_artifacts(
        self,
        company_root: Path,
        request: CompanyRunExecutionRequest,
        phase_records: list[CompanyRunPhaseRecord],
    ) -> None:
        """Write planning artifacts. Args: company_root: Root; request: Request; phase_records: Log."""
        write_company_run_planning_artifacts(
            company_root=company_root,
            request=request,
            phase_records=phase_records,
        )

    def write_executive_gate(
        self,
        company_root: Path,
        roster: CompanyRunRoster,
        phase_records: list[CompanyRunPhaseRecord],
        vote_records: list[CompanyRunVoteRecord],
    ) -> None:
        """Write executive gate. Args: company_root: Root; roster: Roster; phase_records: Log; vote_records: Votes."""
        write_company_run_executive_gate(
            company_root=company_root,
            roster=roster,
            phase_records=phase_records,
            vote_records=vote_records,
        )

    def write_implementation_kickoff(
        self,
        company_root: Path,
        request: CompanyRunExecutionRequest,
        phase_records: list[CompanyRunPhaseRecord],
    ) -> None:
        """Write implementation kickoff. Args: company_root: Root; request: Request; phase_records: Log."""
        write_company_run_implementation_kickoff(
            company_root=company_root,
            request=request,
            phase_records=phase_records,
        )

    def run_team_gate(
        self,
        paths: ActualRunPaths,
        cwd: Path,
        company_root: Path,
        request: CompanyRunExecutionRequest,
        live_team_allowed: bool,
        phase_records: list[CompanyRunPhaseRecord],
    ) -> CompanyRunTeamLaunchRecord:
        """Run Team gate. Args: paths: Paths; cwd: Repo; company_root: Root; request: Request; live_team_allowed: Policy; phase_records: Log. Returns: CompanyRunTeamLaunchRecord: Launch record."""
        team_record = run_team_gate_for_company_run(
            paths=paths,
            cwd=cwd,
            company_root=company_root,
            request=request,
            live_team_allowed=live_team_allowed,
            phase_records=phase_records,
            team_launcher=self._team_launcher,
        )
        return team_record

    def write_post_team_gates(
        self,
        company_root: Path,
        phase_records: list[CompanyRunPhaseRecord],
        team_status: CompanyRunTeamLaunchStatus,
    ) -> None:
        """Write post-Team gates. Args: company_root: Root; phase_records: Log; team_status: Team status."""
        write_post_team_gates_for_company_run(
            company_root=company_root,
            phase_records=phase_records,
            team_status=team_status,
        )


def _discovery_gate_phase_summary(should_continue: bool) -> str:
    """Build Gate 0 phase summary. Args: should_continue: Gate decision. Returns: str: Phase summary."""
    if should_continue:
        summary = "Discovery/ROI gate accepted company-run."
        return summary
    summary = "Discovery/ROI gate stopped company-run before expensive work."
    return summary


def _discovery_gate_phase_status(should_continue: bool) -> CompanyRunPhaseStatus:
    """Build Gate 0 phase status. Args: should_continue: Gate decision. Returns: CompanyRunPhaseStatus: Phase status."""
    if should_continue:
        status = CompanyRunPhaseStatus.COMPLETE
        return status
    status = CompanyRunPhaseStatus.REQUIRES_AGENT_ACTION
    return status
