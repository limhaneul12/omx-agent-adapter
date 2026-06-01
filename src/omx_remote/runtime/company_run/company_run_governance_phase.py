from pathlib import Path

from omx_remote.runtime.company_run.company_run_artifacts import (
    artifact_record,
    write_company_json,
    write_company_markdown,
)
from omx_remote.runtime.company_run.company_run_phase_log import (
    append_company_run_phase,
)
from omx_remote.runtime.company_run.company_run_phase_texts import (
    execution_brief_markdown,
    kickoff_markdown,
    prd_markdown,
    risks_markdown,
    test_spec_markdown,
)
from omx_remote.runtime.company_run.company_run_result_persistence import (
    artifact_kind_for_planning_file,
)
from omx_remote.runtime.company_run.company_run_vote_engine import unanimous_vote_record
from omx_remote.schemas.company_run_schemas import (
    CompanyRunArtifactRecord,
    CompanyRunExecutionRequest,
    CompanyRunPhaseRecord,
    CompanyRunReadinessVerdictPayload,
    CompanyRunRoster,
    CompanyRunTeamPlanPayload,
    CompanyRunVoteRecord,
)
from omx_remote.shared.omx_enums.company_run_enums import (
    CompanyRunArtifactKind,
    CompanyRunPhase,
    CompanyRunRoleGroup,
    CompanyRunVoteChoice,
)


def write_company_run_research_vote(
    company_root: Path,
    roster: CompanyRunRoster,
    phase_records: list[CompanyRunPhaseRecord],
    vote_records: list[CompanyRunVoteRecord],
) -> None:
    """Write the research-completion decision record.

    Args:
        company_root [Path]: Company-run artifact root.
        roster [CompanyRunRoster]: Validated company-run roster.
        phase_records [list[CompanyRunPhaseRecord]]: Mutable phase log records.
        vote_records [list[CompanyRunVoteRecord]]: Mutable vote ledger.
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
    write_company_json(path=vote_path, payload=vote)
    append_company_run_phase(
        phase_records,
        CompanyRunPhase.RESEARCH_COMPLETION_VOTE,
        "Research decision recorded.",
        (artifact_record(CompanyRunArtifactKind.VOTE, vote_path),),
        (vote,),
    )


def write_company_run_proceed_vote(
    company_root: Path,
    roster: CompanyRunRoster,
    phase_records: list[CompanyRunPhaseRecord],
    vote_records: list[CompanyRunVoteRecord],
) -> None:
    """Write the proceed-to-PRD decision record.

    Args:
        company_root [Path]: Company-run artifact root.
        roster [CompanyRunRoster]: Validated company-run roster.
        phase_records [list[CompanyRunPhaseRecord]]: Mutable phase log records.
        vote_records [list[CompanyRunVoteRecord]]: Mutable vote ledger.
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
    decision_path = company_root / "decisions" / "orchestrator-decision.md"
    write_company_json(path=vote_path, payload=vote)
    write_company_markdown(
        path=decision_path,
        text=(
            "# Orchestrator decision\n\n"
            "Proceed to PRD; implementation remains blocked until readiness gates pass.\n"
        ),
    )
    append_company_run_phase(
        phase_records,
        CompanyRunPhase.PROCEED_VOTE,
        "Proceed decision recorded.",
        (artifact_record(CompanyRunArtifactKind.VOTE, vote_path),),
        (vote,),
    )


def write_company_run_planning_artifacts(
    company_root: Path,
    request: CompanyRunExecutionRequest,
    phase_records: list[CompanyRunPhaseRecord],
) -> None:
    """Write PRD, test spec, execution brief, risks, and readiness verdict.

    Args:
        company_root [Path]: Company-run artifact root.
        request [CompanyRunExecutionRequest]: Execution request.
        phase_records [list[CompanyRunPhaseRecord]]: Mutable phase log records.
    """
    planning_texts = (
        ("prd.md", prd_markdown(request.objective)),
        ("test-spec.md", test_spec_markdown(request.objective)),
        ("execution-brief.md", execution_brief_markdown(request.objective)),
        ("risks-and-decisions.md", risks_markdown()),
    )
    artifacts = [
        _write_planning_markdown(
            company_root=company_root,
            filename=filename,
            text=text,
        )
        for filename, text in planning_texts
    ]
    readiness_path = company_root / "planning" / "readiness-verdict.json"
    readiness_payload = CompanyRunReadinessVerdictPayload(
        verdict="ready-for-executive-review"
    )
    write_company_json(path=readiness_path, payload=readiness_payload)
    artifacts.append(artifact_record(CompanyRunArtifactKind.READINESS, readiness_path))
    append_company_run_phase(
        phase_records,
        CompanyRunPhase.IDEA_TO_PRD,
        "PRD, test spec, execution brief, risks, and readiness verdict written.",
        tuple(artifacts),
    )


def write_company_run_executive_gate(
    company_root: Path,
    roster: CompanyRunRoster,
    phase_records: list[CompanyRunPhaseRecord],
    vote_records: list[CompanyRunVoteRecord],
) -> None:
    """Write CTO/CISO/QA/release implementation-readiness gate artifacts.

    Args:
        company_root [Path]: Company-run artifact root.
        roster [CompanyRunRoster]: Validated company-run roster.
        phase_records [list[CompanyRunPhaseRecord]]: Mutable phase log records.
        vote_records [list[CompanyRunVoteRecord]]: Mutable vote ledger.
    """
    review_files = (
        ("cto-review.md", "CTO approves architecture readiness with scoped Team fanout."),
        (
            "ciso-security-review.md",
            "CISO requires secret redaction and no unsafe external side effects.",
        ),
        ("qa-review.md", "QA approves testability with recorded scenarios."),
        (
            "release-manager-review.md",
            "Release manager requires run ledger and memory closeout.",
        ),
    )
    artifacts = [
        _write_executive_review(
            company_root=company_root,
            filename=filename,
            body=body,
        )
        for filename, body in review_files
    ]
    voters = roster.seats_for_group(CompanyRunRoleGroup.EXECUTIVE)[:3]
    vote = unanimous_vote_record(
        vote_id="executive-gate",
        phase=CompanyRunPhase.EXECUTIVE_READINESS_GATE,
        voters=voters,
        decision=CompanyRunVoteChoice.READY_FOR_IMPLEMENTATION,
        rationale=(
            "Executive council allows implementation-kickoff only after planning "
            "artifacts exist."
        ),
        threshold="minimum 3 executive council voters",
    )
    vote_records.append(vote)
    gate_path = company_root / "executive" / "executive-gate.json"
    write_company_json(path=gate_path, payload=vote)
    artifacts.append(artifact_record(CompanyRunArtifactKind.VOTE, gate_path))
    append_company_run_phase(
        phase_records,
        CompanyRunPhase.EXECUTIVE_READINESS_GATE,
        "Executive implementation-readiness gate passed.",
        tuple(artifacts),
        (vote,),
    )


def write_company_run_implementation_kickoff(
    company_root: Path,
    request: CompanyRunExecutionRequest,
    phase_records: list[CompanyRunPhaseRecord],
) -> None:
    """Write the post-planning implementation-kickoff gate.

    Args:
        company_root [Path]: Company-run artifact root.
        request [CompanyRunExecutionRequest]: Execution request.
        phase_records [list[CompanyRunPhaseRecord]]: Mutable phase log records.
    """
    kickoff_path = company_root / "implementation" / "implementation-kickoff.md"
    team_plan_path = company_root / "implementation" / "team-plan.json"
    team_plan_payload = CompanyRunTeamPlanPayload(
        worker_count=request.worker_count,
        team_required=True,
        scoped_subagents_required=True,
        implementation_before_prd_allowed=False,
    )
    write_company_markdown(path=kickoff_path, text=kickoff_markdown(request.objective))
    write_company_json(path=team_plan_path, payload=team_plan_payload)
    append_company_run_phase(
        phase_records,
        CompanyRunPhase.IMPLEMENTATION_KICKOFF,
        "Implementation-kickoff gate opened Team bootstrap after PRD/test/brief readiness.",
        (
            artifact_record(CompanyRunArtifactKind.READINESS, kickoff_path),
            artifact_record(CompanyRunArtifactKind.TEAM, team_plan_path),
        ),
    )


def _write_planning_markdown(
    company_root: Path,
    filename: str,
    text: str,
) -> CompanyRunArtifactRecord:
    """Write one planning artifact. Args: company_root: Root; filename: Name; text: Body. Returns: CompanyRunArtifactRecord: Artifact record."""
    path = company_root / "planning" / filename
    write_company_markdown(path=path, text=text)
    record = artifact_record(artifact_kind_for_planning_file(filename), path)
    return record


def _write_executive_review(
    company_root: Path,
    filename: str,
    body: str,
) -> CompanyRunArtifactRecord:
    """Write one executive review. Args: company_root: Root; filename: Name; body: Body. Returns: CompanyRunArtifactRecord: Artifact record."""
    path = company_root / "executive" / filename
    write_company_markdown(path=path, text=f"# {filename}\n\n{body}\n")
    record = artifact_record(CompanyRunArtifactKind.READINESS, path)
    return record
