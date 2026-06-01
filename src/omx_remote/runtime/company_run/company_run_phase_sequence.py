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
from omx_remote.runtime.company_run.company_run_phase_log import (
    append_company_run_phase,
)
from omx_remote.runtime.company_run.company_run_phase_texts import (
    execution_brief_markdown,
    kickoff_markdown,
    memory_recall_markdown,
    prd_markdown,
    risks_markdown,
    test_spec_markdown,
)
from omx_remote.runtime.company_run.company_run_result_persistence import (
    artifact_kind_for_planning_file,
)
from omx_remote.runtime.company_run.company_run_team_phase import (
    run_team_gate_for_company_run,
    write_post_team_gates_for_company_run,
)
from omx_remote.runtime.company_run.company_run_vote_engine import unanimous_vote_record
from omx_remote.schemas.company_run_schemas import (
    CompanyRunExecutionRequest,
    CompanyRunPhaseRecord,
    CompanyRunReadinessVerdictPayload,
    CompanyRunRoster,
    CompanyRunRouteNextArtifactPayload,
    CompanyRunTeamLaunchRecord,
    CompanyRunTeamPlanPayload,
    CompanyRunVoteRecord,
)
from omx_remote.shared.omx_enums.company_run_enums import (
    CompanyRunArtifactKind,
    CompanyRunPhase,
    CompanyRunRoleGroup,
    CompanyRunTeamLaunchStatus,
    CompanyRunVoteChoice,
)


class CompanyRunPhaseSequence:
    """Write ordered company-run phase artifacts and gate votes."""

    def __init__(self, team_launcher=None) -> None:
        """Initialize the phase sequence writer.

        Args:
            team_launcher: Optional injected Team launcher used by tests or
                alternate runtimes to observe the Team request without spawning
                native OMX Team directly.
        """
        self._team_launcher = team_launcher

    def write_memory_and_route_artifacts(
        self,
        company_root: Path,
        request: CompanyRunExecutionRequest,
        phase_records: list[CompanyRunPhaseRecord],
    ) -> None:
        """Write memory-recall and route-next gate artifacts.

        Args:
            company_root: Directory that owns the current company-run artifacts.
            request: Execution request containing objective and policy inputs.
            phase_records: Mutable phase log to update after writing artifacts.
        """
        memory_path = company_root / "memory-recall.md"
        write_company_markdown(memory_path, memory_recall_markdown(request.objective))
        route_path = company_root / "route-next.json"
        route_payload = CompanyRunRouteNextArtifactPayload(
            route="company-run",
            team_required=True,
            subagents_required=True,
            one_agent_show_allowed=False,
            objective=request.objective,
        )
        write_company_json(
            route_path,
            route_payload,
        )
        append_company_run_phase(
            phase_records,
            CompanyRunPhase.MEMORY_RECALL,
            "Alexandria MCP memory recall points recorded.",
            (artifact_record(CompanyRunArtifactKind.MEMORY, memory_path),),
        )
        append_company_run_phase(
            phase_records,
            CompanyRunPhase.ROUTE_NEXT,
            "route-next gate selected company-run with Team/subagent requirements.",
            (artifact_record(CompanyRunArtifactKind.STATE, route_path),),
        )

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
        """Run independent research council lanes and record their artifacts.

        Args:
            paths: Actual-run artifact paths used for subagent attempt logs.
            cwd: Repository root that the company-run command is operating on.
            company_root: Directory that owns the current company-run artifacts.
            request: Execution request containing objective and timeouts.
            roster: Validated company roster used to assign council seats.
            phase_records: Mutable phase log to update after lane completion.
            council_mode: Council execution mode, for example artifact fallback
                or Codex subagent execution.

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
        """Write the research-completion vote.

        Args:
            company_root: Directory that owns the current company-run artifacts.
            roster: Validated company roster used to select voters.
            phase_records: Mutable phase log to update after the vote.
            vote_records: Mutable vote ledger to append the recorded vote to.
        """
        voters = roster.seats_for_group(CompanyRunRoleGroup.RESEARCH)[:3]
        vote = unanimous_vote_record(
            vote_id="research-vote",
            phase=CompanyRunPhase.RESEARCH_COMPLETION_VOTE,
            voters=voters,
            decision=CompanyRunVoteChoice.RESEARCH_COMPLETE,
            rationale="Research council found enough evidence to proceed to the proceed vote.",
            threshold="minimum 3 research council voters",
        )
        vote_records.append(vote)
        vote_path = company_root / "research" / "research-vote.json"
        write_company_json(vote_path, vote)
        append_company_run_phase(
            phase_records,
            CompanyRunPhase.RESEARCH_COMPLETION_VOTE,
            "Research completion vote recorded.",
            (artifact_record(CompanyRunArtifactKind.VOTE, vote_path),),
            (vote,),
        )

    def write_proceed_vote(
        self,
        company_root: Path,
        roster: CompanyRunRoster,
        phase_records: list[CompanyRunPhaseRecord],
        vote_records: list[CompanyRunVoteRecord],
    ) -> None:
        """Write the proceed-to-PRD decision vote.

        Args:
            company_root: Directory that owns the current company-run artifacts.
            roster: Validated company roster used to select voters.
            phase_records: Mutable phase log to update after the vote.
            vote_records: Mutable vote ledger to append the recorded vote to.
        """
        voters = (
            roster.seats_for_group(CompanyRunRoleGroup.CEO)[0],
            *roster.seats_for_group(CompanyRunRoleGroup.RESEARCH)[:2],
        )
        vote = unanimous_vote_record(
            vote_id="proceed-vote",
            phase=CompanyRunPhase.PROCEED_VOTE,
            voters=voters,
            decision=CompanyRunVoteChoice.PROCEED_TO_PRD,
            rationale="Proceed to PRD with risks and gates preserved.",
            threshold="CEO plus research council majority",
        )
        vote_records.append(vote)
        vote_path = company_root / "decisions" / "proceed-vote.json"
        write_company_json(vote_path, vote)
        write_company_markdown(
            company_root / "decisions" / "orchestrator-decision.md",
            "# Orchestrator decision\n\nProceed to PRD; implementation remains blocked until readiness gates pass.\n",
        )
        append_company_run_phase(
            phase_records,
            CompanyRunPhase.PROCEED_VOTE,
            "Proceed vote recorded.",
            (artifact_record(CompanyRunArtifactKind.VOTE, vote_path),),
            (vote,),
        )

    def write_planning_artifacts(
        self,
        company_root: Path,
        request: CompanyRunExecutionRequest,
        phase_records: list[CompanyRunPhaseRecord],
    ) -> None:
        """Write PRD, test spec, execution brief, risks, and readiness verdict.

        Args:
            company_root: Directory that owns the current company-run artifacts.
            request: Execution request containing the product objective.
            phase_records: Mutable phase log to update after planning artifacts.
        """
        planning_texts = {
            "prd.md": prd_markdown(request.objective),
            "test-spec.md": test_spec_markdown(request.objective),
            "execution-brief.md": execution_brief_markdown(request.objective),
            "risks-and-decisions.md": risks_markdown(),
        }
        artifacts = []
        for filename, text in planning_texts.items():
            path = company_root / "planning" / filename
            write_company_markdown(path, text)
            artifacts.append(
                artifact_record(artifact_kind_for_planning_file(filename), path)
            )
        readiness_path = company_root / "planning" / "readiness-verdict.json"
        readiness_payload = CompanyRunReadinessVerdictPayload(
            verdict="ready-for-executive-review"
        )
        write_company_json(readiness_path, readiness_payload)
        artifacts.append(
            artifact_record(CompanyRunArtifactKind.READINESS, readiness_path)
        )
        append_company_run_phase(
            phase_records,
            CompanyRunPhase.IDEA_TO_PRD,
            "PRD, test spec, execution brief, risks, and readiness verdict written.",
            tuple(artifacts),
        )

    def write_executive_gate(
        self,
        company_root: Path,
        roster: CompanyRunRoster,
        phase_records: list[CompanyRunPhaseRecord],
        vote_records: list[CompanyRunVoteRecord],
    ) -> None:
        """Write executive CTO/CISO/QA/release readiness gate artifacts.

        Args:
            company_root: Directory that owns the current company-run artifacts.
            roster: Validated company roster used to select executive voters.
            phase_records: Mutable phase log to update after the gate.
            vote_records: Mutable vote ledger to append the gate vote to.
        """
        review_files = {
            "cto-review.md": "CTO approves architecture readiness with scoped Team fanout.",
            "ciso-security-review.md": "CISO requires secret redaction and no unsafe external side effects.",
            "qa-review.md": "QA approves testability with recorded scenarios.",
            "release-manager-review.md": "Release manager requires run ledger and memory closeout.",
        }
        artifacts = []
        for filename, body in review_files.items():
            path = company_root / "executive" / filename
            write_company_markdown(path, f"# {filename}\n\n{body}\n")
            artifacts.append(artifact_record(CompanyRunArtifactKind.READINESS, path))
        voters = roster.seats_for_group(CompanyRunRoleGroup.EXECUTIVE)[:3]
        vote = unanimous_vote_record(
            vote_id="executive-gate",
            phase=CompanyRunPhase.EXECUTIVE_READINESS_GATE,
            voters=voters,
            decision=CompanyRunVoteChoice.READY_FOR_IMPLEMENTATION,
            rationale="Executive council allows implementation-kickoff only after planning artifacts exist.",
            threshold="minimum 3 executive council voters",
        )
        vote_records.append(vote)
        gate_path = company_root / "executive" / "executive-gate.json"
        write_company_json(gate_path, vote)
        artifacts.append(artifact_record(CompanyRunArtifactKind.VOTE, gate_path))
        append_company_run_phase(
            phase_records,
            CompanyRunPhase.EXECUTIVE_READINESS_GATE,
            "Executive implementation-readiness gate passed.",
            tuple(artifacts),
            (vote,),
        )

    def write_implementation_kickoff(
        self,
        company_root: Path,
        request: CompanyRunExecutionRequest,
        phase_records: list[CompanyRunPhaseRecord],
    ) -> None:
        """Write the post-planning implementation-kickoff gate.

        Args:
            company_root: Directory that owns the current company-run artifacts.
            request: Execution request containing worker-count policy.
            phase_records: Mutable phase log to update after kickoff.
        """
        kickoff_path = company_root / "implementation" / "implementation-kickoff.md"
        write_company_markdown(kickoff_path, kickoff_markdown(request.objective))
        team_plan_path = company_root / "implementation" / "team-plan.json"
        team_plan_payload = CompanyRunTeamPlanPayload(
            worker_count=request.worker_count,
            team_required=True,
            scoped_subagents_required=True,
            implementation_before_prd_allowed=False,
        )
        write_company_json(team_plan_path, team_plan_payload)
        append_company_run_phase(
            phase_records,
            CompanyRunPhase.IMPLEMENTATION_KICKOFF,
            "Implementation-kickoff gate opened Team bootstrap after PRD/test/brief readiness.",
            (
                artifact_record(CompanyRunArtifactKind.READINESS, kickoff_path),
                artifact_record(CompanyRunArtifactKind.TEAM, team_plan_path),
            ),
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
        """Record or launch the mandatory Team bootstrap gate.

        Args:
            paths: Actual-run artifact paths used for launch attempt logs.
            cwd: Repository root that the company-run command is operating on.
            company_root: Directory that owns the current company-run artifacts.
            request: Execution request containing objective and Team policy.
            live_team_allowed: Whether native OMX Team may be launched now.
            phase_records: Mutable phase log to update after Team bootstrap.

        Returns:
            The Team launch record that was persisted for this run.
        """
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
        """Write team-sync, integration, review, release, and memory closeout gates.

        Args:
            company_root: Directory that owns the current company-run artifacts.
            phase_records: Mutable phase log to update after post-Team gates.
            team_status: Team launch outcome used to decide review/release
                readiness verdicts.
        """
        write_post_team_gates_for_company_run(
            company_root=company_root,
            phase_records=phase_records,
            team_status=team_status,
        )
