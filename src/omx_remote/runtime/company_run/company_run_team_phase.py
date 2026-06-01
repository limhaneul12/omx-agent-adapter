from collections.abc import Callable
from pathlib import Path

from pydantic import ValidationError

from omx_remote.runtime.commands.artifacts.actual_run_record_writer import (
    ActualRunPaths,
)
from omx_remote.runtime.commands.planning.command_runtime_options import (
    team_worker_launch_args,
)
from omx_remote.runtime.company_run.company_run_artifacts import (
    artifact_record,
    write_company_json,
    write_company_markdown,
)
from omx_remote.runtime.company_run.company_run_phase_log import (
    append_company_run_phase,
)
from omx_remote.runtime.company_run.company_run_team_runtime import (
    build_team_task,
    launch_company_run_team,
)
from omx_remote.runtime.company_run.company_run_worker_dispatch import (
    build_worker_dispatch_payload,
)
from omx_remote.runtime.company_run.phase_gates import (
    validate_phase_gate_order,
    validate_team_bootstrap_readiness,
)
from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel
from omx_remote.schemas.company_run_schemas import (
    CompanyRunBootstrapVoteEvidence,
    CompanyRunBootstrapVoteOutcomes,
    CompanyRunExecutionRequest,
    CompanyRunPhaseRecord,
    CompanyRunReadinessVerdictPayload,
    CompanyRunRequiredBootstrapVote,
    CompanyRunTeamBootstrapArtifacts,
    CompanyRunTeamLaunchRecord,
    CompanyRunTeamRequest,
    CompanyRunVoteRecord,
    CompanyRunWorkerDispatchPayload,
)
from omx_remote.shared.omx_enums.company_run_enums import (
    CompanyRunArtifactKind,
    CompanyRunBootstrapVoteId,
    CompanyRunPhase,
    CompanyRunPhaseStatus,
    CompanyRunTeamLaunchStatus,
    CompanyRunVoteChoice,
)

TeamLauncher = Callable[[CompanyRunTeamRequest], object]

_RESEARCH_COMPLETION_VOTE = CompanyRunRequiredBootstrapVote(
    gate_id=CompanyRunBootstrapVoteId.RESEARCH_COMPLETION,
    relative_path="research/research-vote.json",
    vote_id="research-vote",
    phase=CompanyRunPhase.RESEARCH_COMPLETION_VOTE,
    expected_decision=CompanyRunVoteChoice.RESEARCH_COMPLETE,
)
_PROCEED_VOTE = CompanyRunRequiredBootstrapVote(
    gate_id=CompanyRunBootstrapVoteId.PROCEED,
    relative_path="decisions/proceed-vote.json",
    vote_id="proceed-vote",
    phase=CompanyRunPhase.PROCEED_VOTE,
    expected_decision=CompanyRunVoteChoice.PROCEED_TO_PRD,
)
_EXECUTIVE_GATE_VOTE = CompanyRunRequiredBootstrapVote(
    gate_id=CompanyRunBootstrapVoteId.EXECUTIVE_GATE,
    relative_path="executive/executive-gate.json",
    vote_id="executive-gate",
    phase=CompanyRunPhase.EXECUTIVE_READINESS_GATE,
    expected_decision=CompanyRunVoteChoice.READY_FOR_IMPLEMENTATION,
)


def run_team_gate_for_company_run(
    paths: ActualRunPaths,
    cwd: Path,
    company_root: Path,
    request: CompanyRunExecutionRequest,
    live_team_allowed: bool,
    phase_records: list[CompanyRunPhaseRecord],
    team_launcher: TeamLauncher | None,
) -> CompanyRunTeamLaunchRecord:
    """Record or launch the mandatory Team bootstrap gate.

    Args:
        paths [ActualRunPaths]: Actual-run artifact paths for launch attempts.
        cwd [Path]: Repository root that company-run operates on.
        company_root [Path]: Directory that owns company-run artifacts.
        request [CompanyRunExecutionRequest]: Company-run request.
        live_team_allowed [bool]: Whether native OMX Team launch may run now.
        phase_records [list[CompanyRunPhaseRecord]]: Mutable phase log.
        team_launcher [TeamLauncher | None]: Optional injected Team launcher.

    Returns:
        CompanyRunTeamLaunchRecord: Persisted Team launch record.
    """
    team_task = build_team_task(
        objective=request.objective,
        company_root=company_root,
        runtime_options=request.runtime_options,
    )
    team_request = CompanyRunTeamRequest(
        native_argv=("omx", "team", f"{request.worker_count}:executor", team_task),
        worker_count=request.worker_count,
        objective=request.objective,
        team_task=team_task,
        runtime_options=request.runtime_options,
    )
    completed_phases = tuple(record.phase for record in phase_records)
    order_verdict = validate_phase_gate_order(
        completed_phases=completed_phases,
        next_phase=CompanyRunPhase.TEAM_BOOTSTRAP,
    )
    artifact_evidence = _team_bootstrap_artifact_evidence(company_root=company_root)
    vote_evidence = _team_bootstrap_vote_evidence(company_root=company_root)
    readiness_verdict = validate_team_bootstrap_readiness(
        completed_phases=completed_phases,
        artifacts=artifact_evidence,
        votes=vote_evidence.outcomes,
    )
    if not order_verdict.allowed or not readiness_verdict.allowed:
        blockers = (
            *order_verdict.blocked_reasons,
            *vote_evidence.blocked_reasons,
            *readiness_verdict.blocked_reasons,
        )
        team_record = _blocked_team_record(
            company_root=company_root,
            request=team_request,
            blockers=blockers,
        )
    elif team_launcher is not None:
        dispatch_path = _write_team_dispatch_packets(
            company_root=company_root,
            request=team_request,
        )
        team_launcher(team_request)
        team_record = _team_launch_record_from_dispatch(
            company_root=company_root,
            request=team_request,
            dispatch_path=dispatch_path,
            note="Team dispatch packets were written before the injected Team launcher callback.",
        )
    elif live_team_allowed or str(request.team_launch_mode) == "handoff":
        team_record, _ = launch_company_run_team(
            paths=paths,
            cwd=cwd,
            objective=request.objective,
            company_root=company_root,
            worker_count=request.worker_count,
            timeout_seconds=request.timeout_seconds,
            step_index=2,
            launch_mode=str(request.team_launch_mode),
            runtime_options=request.runtime_options,
        )
    else:
        team_record = _planned_team_record(
            company_root=company_root,
            request=team_request,
        )
    team_launch_path = company_root / "implementation" / "team-launch.json"
    write_company_json(team_launch_path, team_record)
    phase_status = _team_bootstrap_phase_status(team_status=team_record.status)
    phase_blockers = _team_bootstrap_phase_blockers(team_record=team_record)
    append_company_run_phase(
        phase_records=phase_records,
        phase=CompanyRunPhase.TEAM_BOOTSTRAP,
        summary=f"Team bootstrap recorded with status {team_record.status}.",
        artifacts=(
            artifact_record(
                kind=CompanyRunArtifactKind.TEAM,
                path=Path(team_record.dispatch_path),
            ),
            artifact_record(kind=CompanyRunArtifactKind.TEAM, path=team_launch_path),
        ),
        status=phase_status,
        blocked_reasons=phase_blockers,
    )
    return team_record


def write_post_team_gates_for_company_run(
    company_root: Path,
    phase_records: list[CompanyRunPhaseRecord],
    team_status: CompanyRunTeamLaunchStatus,
) -> None:
    """Write team-sync, integration, review, release, and memory closeout gates.

    Args:
        company_root [Path]: Directory that owns company-run artifacts.
        phase_records [list[CompanyRunPhaseRecord]]: Mutable phase log.
        team_status [CompanyRunTeamLaunchStatus]: Team launch outcome.
    """
    for relative_path, body in _post_team_files().items():
        write_company_markdown(
            path=company_root / relative_path,
            text=f"# {relative_path}\n\n{body}\n",
        )
    review_gate_path = company_root / "review" / "review-gate.json"
    release_path = company_root / "release" / "release-readiness.json"
    review_status = (
        "approve"
        if team_status == CompanyRunTeamLaunchStatus.COMPLETED
        else "requires_agent_action"
    )
    release_status = (
        "ready"
        if team_status == CompanyRunTeamLaunchStatus.COMPLETED
        else "not_ready_team_follow_up_required"
    )
    review_payload = CompanyRunReadinessVerdictPayload(verdict=review_status)
    release_payload = CompanyRunReadinessVerdictPayload(verdict=release_status)
    write_company_json(review_gate_path, review_payload)
    write_company_json(release_path, release_payload)
    append_company_run_phase(
        phase_records=phase_records,
        phase=CompanyRunPhase.TEAM_SYNC_LOOP,
        summary="Team sync loop recorded.",
        artifacts=(
            artifact_record(
                kind=CompanyRunArtifactKind.TEAM,
                path=company_root / "team" / "team-sync.md",
            ),
        ),
    )
    phase_status = (
        CompanyRunPhaseStatus.COMPLETE
        if team_status == CompanyRunTeamLaunchStatus.COMPLETED
        else CompanyRunPhaseStatus.REQUIRES_AGENT_ACTION
    )
    blockers = (
        ()
        if team_status == CompanyRunTeamLaunchStatus.COMPLETED
        else ("OMX Team follow-up is required before dependent gates can complete.",)
    )
    append_company_run_phase(
        phase_records=phase_records,
        phase=CompanyRunPhase.INTEGRATION_PLAN_LOOP,
        summary="Integration plan loop recorded.",
        artifacts=(
            artifact_record(
                kind=CompanyRunArtifactKind.INTEGRATION,
                path=company_root / "team" / "integration-plan.md",
            ),
        ),
        status=phase_status,
        blocked_reasons=blockers,
    )
    append_company_run_phase(
        phase_records=phase_records,
        phase=CompanyRunPhase.REVIEW_GATE_LOOP,
        summary="Review/security/architecture/QA gate recorded.",
        artifacts=(
            artifact_record(kind=CompanyRunArtifactKind.REVIEW, path=review_gate_path),
        ),
        status=phase_status,
        blocked_reasons=blockers,
    )
    append_company_run_phase(
        phase_records=phase_records,
        phase=CompanyRunPhase.RELEASE_READINESS,
        summary="Release readiness verdict recorded.",
        artifacts=(
            artifact_record(kind=CompanyRunArtifactKind.RELEASE, path=release_path),
        ),
        status=phase_status,
        blocked_reasons=blockers,
    )
    append_company_run_phase(
        phase_records=phase_records,
        phase=CompanyRunPhase.MEMORY_CLOSEOUT,
        summary="Alexandria MCP memory closeout point recorded.",
        artifacts=(
            artifact_record(
                kind=CompanyRunArtifactKind.MEMORY,
                path=company_root / "memory-closeout.md",
            ),
        ),
        status=phase_status,
        blocked_reasons=blockers,
    )


def _team_bootstrap_artifact_evidence(
    company_root: Path,
) -> CompanyRunTeamBootstrapArtifacts:
    """Collect required artifact existence evidence for Team bootstrap.

    Args:
        company_root [Path]: Directory that owns company-run artifacts.

    Returns:
        CompanyRunTeamBootstrapArtifacts: Typed artifact gate evidence.
    """
    evidence = CompanyRunTeamBootstrapArtifacts(
        planning_prd=(company_root / "planning" / "prd.md").is_file(),
        planning_test_spec=(company_root / "planning" / "test-spec.md").is_file(),
        planning_execution_brief=(
            company_root / "planning" / "execution-brief.md"
        ).is_file(),
        planning_readiness_verdict=(
            company_root / "planning" / "readiness-verdict.json"
        ).is_file(),
        implementation_kickoff=(
            company_root / "implementation" / "implementation-kickoff.md"
        ).is_file(),
    )
    return evidence


def _team_bootstrap_vote_evidence(
    company_root: Path,
) -> CompanyRunBootstrapVoteEvidence:
    """Read and validate the vote files required before Team bootstrap.

    Args:
        company_root [Path]: Directory that owns company-run artifacts.

    Returns:
        CompanyRunBootstrapVoteEvidence: Vote outcomes plus file/schema blockers.
    """
    research_vote = _read_required_bootstrap_vote(
        company_root=company_root,
        vote_spec=_RESEARCH_COMPLETION_VOTE,
    )
    proceed_vote = _read_required_bootstrap_vote(
        company_root=company_root,
        vote_spec=_PROCEED_VOTE,
    )
    executive_vote = _read_required_bootstrap_vote(
        company_root=company_root,
        vote_spec=_EXECUTIVE_GATE_VOTE,
    )
    evidence = CompanyRunBootstrapVoteEvidence(
        outcomes=CompanyRunBootstrapVoteOutcomes(
            research_completion=research_vote.decision,
            proceed=proceed_vote.decision,
            executive_gate=executive_vote.decision,
        ),
        blocked_reasons=(
            *research_vote.blocked_reasons,
            *proceed_vote.blocked_reasons,
            *executive_vote.blocked_reasons,
        ),
    )
    return evidence


class _RequiredVoteReadResult(StrictSchemaModel):
    """Internal result for one required bootstrap vote artifact."""

    decision: CompanyRunVoteChoice
    blocked_reasons: tuple[NonEmptyString, ...]


def _read_required_bootstrap_vote(
    company_root: Path,
    vote_spec: CompanyRunRequiredBootstrapVote,
) -> _RequiredVoteReadResult:
    """Read one required Team-bootstrap vote file as a typed vote record.

    Args:
        company_root [Path]: Directory that owns company-run artifacts.
        vote_spec [CompanyRunRequiredBootstrapVote]: Expected vote contract.

    Returns:
        _RequiredVoteReadResult: Decision and blockers for one vote file.
    """
    vote_path = company_root / vote_spec.relative_path
    if not vote_path.is_file():
        result = _RequiredVoteReadResult(
            decision=CompanyRunVoteChoice.BLOCK,
            blocked_reasons=(
                f"missing required vote artifact: {vote_spec.relative_path}",
            ),
        )
        return result
    try:
        vote_record = CompanyRunVoteRecord.model_validate_json(vote_path.read_bytes())
    except (OSError, ValidationError, ValueError) as error:
        result = _RequiredVoteReadResult(
            decision=CompanyRunVoteChoice.BLOCK,
            blocked_reasons=(
                f"invalid required vote artifact {vote_spec.relative_path}: {error}",
            ),
        )
        return result

    identity_blockers = _required_vote_identity_blockers(
        vote_spec=vote_spec,
        vote_record=vote_record,
    )
    decision = (
        vote_record.decision if not identity_blockers else CompanyRunVoteChoice.BLOCK
    )
    result = _RequiredVoteReadResult(
        decision=decision,
        blocked_reasons=identity_blockers,
    )
    return result


def _required_vote_identity_blockers(
    vote_spec: CompanyRunRequiredBootstrapVote,
    vote_record: CompanyRunVoteRecord,
) -> tuple[str, ...]:
    """Return identity blockers for a vote file that parsed successfully.

    Args:
        vote_spec [CompanyRunRequiredBootstrapVote]: Expected vote contract.
        vote_record [CompanyRunVoteRecord]: Parsed vote record.

    Returns:
        tuple[str, ...]: Identity mismatch blockers.
    """
    blockers = [
        (
            f"invalid vote_id in {vote_spec.relative_path}: expected "
            f"{vote_spec.vote_id}, got {vote_record.vote_id}"
        )
        for expected, actual in ((vote_spec.vote_id, vote_record.vote_id),)
        if actual != expected
    ]
    blockers.extend(
        (
            f"invalid vote phase in {vote_spec.relative_path}: expected "
            f"{vote_spec.phase.value}, got {vote_record.phase.value}"
        )
        for expected, actual in ((vote_spec.phase, vote_record.phase),)
        if actual != expected
    )
    return tuple(blockers)


def _team_bootstrap_phase_status(
    team_status: CompanyRunTeamLaunchStatus,
) -> CompanyRunPhaseStatus:
    """Map a Team launch status to the persisted Team bootstrap phase status.

    Args:
        team_status [CompanyRunTeamLaunchStatus]: Runtime Team launch outcome.

    Returns:
        CompanyRunPhaseStatus: Phase ledger status.
    """
    if team_status == CompanyRunTeamLaunchStatus.COMPLETED:
        return CompanyRunPhaseStatus.COMPLETE
    if team_status == CompanyRunTeamLaunchStatus.FAILED:
        return CompanyRunPhaseStatus.BLOCKED
    return CompanyRunPhaseStatus.REQUIRES_AGENT_ACTION


def _team_bootstrap_phase_blockers(
    team_record: CompanyRunTeamLaunchRecord,
) -> tuple[str, ...]:
    """Return bootstrap phase blockers derived from the Team launch record.

    Args:
        team_record [CompanyRunTeamLaunchRecord]: Team launch record.

    Returns:
        tuple[str, ...]: Blockers to persist on non-complete phase records.
    """
    if team_record.status == CompanyRunTeamLaunchStatus.COMPLETED:
        return ()
    return (team_record.note,)


def _blocked_team_record(
    company_root: Path,
    request: CompanyRunTeamRequest,
    blockers: tuple[str, ...],
) -> CompanyRunTeamLaunchRecord:
    """Write worker dispatches and return a blocked Team launch record.

    Args:
        company_root [Path]: Directory that owns company-run artifacts.
        request [CompanyRunTeamRequest]: Team launch request.
        blockers [tuple[str, ...]]: Gate blockers preventing Team launch.

    Returns:
        CompanyRunTeamLaunchRecord: Team launch record with follow-up status.
    """
    dispatch_path = company_root / "team" / "worker-dispatches.json"
    dispatch_path.parent.mkdir(parents=True, exist_ok=True)
    dispatch_payload = CompanyRunWorkerDispatchPayload(
        workers=(),
        blocked_reasons=blockers,
    )
    write_company_json(dispatch_path, dispatch_payload)
    record = CompanyRunTeamLaunchRecord(
        status=CompanyRunTeamLaunchStatus.REQUIRES_AGENT_ACTION,
        command=request.native_argv,
        runtime_options=request.runtime_options,
        worker_launch_args=team_worker_launch_args(
            runtime_options=request.runtime_options,
        ),
        worker_count=request.worker_count,
        dispatch_path=str(dispatch_path),
        launch_stdout_path=str(company_root / "team" / "team-launch.stdout.txt"),
        launch_stderr_path=str(company_root / "team" / "team-launch.stderr.txt"),
        note="Team launch blocked by company-run readiness gates: "
        + "; ".join(blockers),
    )
    return record


def _write_team_dispatch_packets(
    company_root: Path,
    request: CompanyRunTeamRequest,
) -> Path:
    """Write one ownership dispatch packet per requested Team worker.

    Args:
        company_root [Path]: Directory that owns company-run artifacts.
        request [CompanyRunTeamRequest]: Team launch request.

    Returns:
        Path: Worker dispatch artifact path.
    """
    dispatch_path = company_root / "team" / "worker-dispatches.json"
    dispatch_path.parent.mkdir(parents=True, exist_ok=True)
    dispatch_payload = build_worker_dispatch_payload(
        objective=request.objective,
        worker_count=request.worker_count,
        allowed_subagents=("executor", "test-engineer", "code-reviewer"),
        subagent_rule="Scoped subagents only inside this worker boundary.",
    )
    write_company_json(dispatch_path, dispatch_payload)
    return dispatch_path


def _planned_team_record(
    company_root: Path,
    request: CompanyRunTeamRequest,
) -> CompanyRunTeamLaunchRecord:
    """Write scoped worker dispatches for a gated Team handoff.

    Args:
        company_root [Path]: Directory that owns company-run artifacts.
        request [CompanyRunTeamRequest]: Team launch request.

    Returns:
        CompanyRunTeamLaunchRecord: Team launch record requiring follow-up.
    """
    dispatch_path = _write_team_dispatch_packets(
        company_root=company_root,
        request=request,
    )
    record = _team_launch_record_from_dispatch(
        company_root=company_root,
        request=request,
        dispatch_path=dispatch_path,
        note="Team dispatch packets written; live Team launch not allowed for this request.",
    )
    return record


def _team_launch_record_from_dispatch(
    company_root: Path,
    request: CompanyRunTeamRequest,
    dispatch_path: Path,
    note: str,
) -> CompanyRunTeamLaunchRecord:
    """Build the Team launch record after worker dispatch packets exist.

    Args:
        company_root [Path]: Directory that owns company-run artifacts.
        request [CompanyRunTeamRequest]: Team launch request.
        dispatch_path [Path]: Existing worker-dispatches artifact path.
        note [str]: Status note for the launch record.

    Returns:
        CompanyRunTeamLaunchRecord: Team launch record requiring follow-up.
    """
    record = CompanyRunTeamLaunchRecord(
        status=CompanyRunTeamLaunchStatus.REQUIRES_AGENT_ACTION,
        command=request.native_argv,
        runtime_options=request.runtime_options,
        worker_launch_args=team_worker_launch_args(
            runtime_options=request.runtime_options,
        ),
        worker_count=request.worker_count,
        dispatch_path=str(dispatch_path),
        launch_stdout_path=str(company_root / "team" / "team-launch.stdout.txt"),
        launch_stderr_path=str(company_root / "team" / "team-launch.stderr.txt"),
        note=note,
    )
    return record


def _post_team_files() -> dict[str, str]:
    """Return post-Team markdown artifact templates.

    Returns:
        dict[str, str]: Company-run-relative artifact path to markdown body.
    """
    files = {
        "team/team-sync.md": "Team status captured. Follow-up required if live Team did not finish.",
        "team/integration-plan.md": "Integration plan preserves worker ownership and verification order.",
        "review/code-review.md": "Code review gate recorded.",
        "review/security-review.md": "Security review gate recorded.",
        "review/architecture-review.md": "Architecture review gate recorded.",
        "review/qa-verdict.md": "QA verdict gate recorded.",
        "release/release-summary.md": "Release summary recorded from company-run evidence.",
        "memory-closeout.md": "Alexandria MCP closeout point recorded for curated memory save.",
    }
    return files
