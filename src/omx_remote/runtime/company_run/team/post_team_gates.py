from pathlib import Path

from omx_remote.runtime.company_run.artifacts.artifact_writers import (
    artifact_record,
    write_company_json,
    write_company_markdown,
)
from omx_remote.runtime.company_run.artifacts.phase_log import (
    append_company_run_phase,
)
from omx_remote.schemas.company_run.company_run_governance_schemas import (
    CompanyRunEvidenceCheck,
    CompanyRunPhaseRecord,
    CompanyRunReadinessVerdictPayload,
)
from omx_remote.shared.omx_enums.company_run_enums import (
    CompanyRunArtifactKind,
    CompanyRunEvidenceCheckStatus,
    CompanyRunPhase,
    CompanyRunPhaseStatus,
    CompanyRunTeamLaunchStatus,
)


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
    blockers = _post_team_blockers(team_status=team_status)
    for relative_path, body in _post_team_files(blockers=blockers).items():
        write_company_markdown(
            path=company_root / relative_path,
            text=f"# {relative_path}\n\n{body}\n",
        )
    review_gate_path = company_root / "review" / "review-gate.json"
    release_path = company_root / "release" / "release-readiness.json"
    review_checks = _review_evidence_checks(
        company_root=company_root,
        team_status=team_status,
    )
    release_checks = _release_evidence_checks(
        company_root=company_root,
        team_status=team_status,
    )
    review_ready = _checks_passed(checks=review_checks) and not blockers
    release_status = (
        "ready"
        if review_ready and _checks_passed(checks=release_checks)
        else "not_ready_team_follow_up_required"
    )
    review_payload = CompanyRunReadinessVerdictPayload(
        verdict="approve" if review_ready else "requires_agent_action",
        required_checks=review_checks,
        evidence_paths=tuple(check.evidence_path for check in review_checks),
        blocked_reasons=blockers,
        note=_post_team_verdict_note(
            gate="Review gate",
            verdict="approve" if review_ready else "requires_agent_action",
            blockers=blockers,
        ),
    )
    release_payload = CompanyRunReadinessVerdictPayload(
        verdict=release_status,
        required_checks=release_checks,
        evidence_paths=tuple(check.evidence_path for check in release_checks),
        blocked_reasons=blockers if release_status != "ready" else (),
        note=_post_team_verdict_note(
            gate="Release readiness",
            verdict=release_status,
            blockers=blockers,
        ),
    )
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

def _post_team_files(blockers: tuple[str, ...]) -> dict[str, str]:
    """Return post-Team markdown artifact templates.

    Args:
        blockers [tuple[str, ...]]: Current Team-derived blockers.

    Returns:
        dict[str, str]: Company-run-relative artifact path to markdown body.
    """
    blocker_text = _blocker_text(blockers=blockers)
    files = {
        "team/team-sync.md": (
            "Team status captured. Follow-up is required if live Team did not "
            f"finish.\n\n{blocker_text}"
        ),
        "team/integration-plan.md": (
            "Integration plan preserves worker ownership, handoff boundaries, "
            f"and verification order.\n\n{blocker_text}"
        ),
        "review/code-review.md": (
            "Code review gate recorded from concrete Team completion evidence.\n\n"
            f"{blocker_text}"
        ),
        "review/security-review.md": (
            "Security review gate recorded; release remains blocked when Team "
            f"evidence is incomplete.\n\n{blocker_text}"
        ),
        "review/architecture-review.md": (
            "Architecture review gate recorded; release remains blocked when "
            f"integration evidence is incomplete.\n\n{blocker_text}"
        ),
        "review/qa-verdict.md": (
            f"QA verdict gate recorded from verification evidence.\n\n{blocker_text}"
        ),
        "release/release-summary.md": (
            "Release summary recorded from company-run evidence; do not claim "
            f"release readiness while blockers remain.\n\n{blocker_text}"
        ),
        "memory-closeout.md": (
            "Alexandria MCP closeout point recorded for curated memory save "
            f"after verified release evidence.\n\n{blocker_text}"
        ),
    }
    return files


def _review_evidence_checks(
    company_root: Path,
    team_status: CompanyRunTeamLaunchStatus,
) -> tuple[CompanyRunEvidenceCheck, ...]:
    """Build explicit post-Team review evidence checks.

    Args:
        company_root [Path]: Directory that owns company-run artifacts.
        team_status [CompanyRunTeamLaunchStatus]: Team launch outcome.

    Returns:
        tuple[CompanyRunEvidenceCheck, ...]: Review evidence contract.
    """
    status = _evidence_check_status(team_status=team_status)
    checks = (
        _evidence_check(
            company_root=company_root,
            check_id="code_review",
            relative_path="review/code-review.md",
            status=status,
            summary="Code-review evidence must be recorded before release approval.",
        ),
        _evidence_check(
            company_root=company_root,
            check_id="security_review",
            relative_path="review/security-review.md",
            status=status,
            summary="Security evidence must be explicit before release approval.",
        ),
        _evidence_check(
            company_root=company_root,
            check_id="architecture_review",
            relative_path="review/architecture-review.md",
            status=status,
            summary="Architecture evidence must be explicit before release approval.",
        ),
        _evidence_check(
            company_root=company_root,
            check_id="qa_verdict",
            relative_path="review/qa-verdict.md",
            status=status,
            summary="QA verification evidence must be explicit before release approval.",
        ),
    )
    return checks


def _release_evidence_checks(
    company_root: Path,
    team_status: CompanyRunTeamLaunchStatus,
) -> tuple[CompanyRunEvidenceCheck, ...]:
    """Build explicit release-readiness evidence checks.

    Args:
        company_root [Path]: Directory that owns company-run artifacts.
        team_status [CompanyRunTeamLaunchStatus]: Team launch outcome.

    Returns:
        tuple[CompanyRunEvidenceCheck, ...]: Release evidence contract.
    """
    status = _evidence_check_status(team_status=team_status)
    checks = (
        _evidence_check(
            company_root=company_root,
            check_id="integration_plan",
            relative_path="team/integration-plan.md",
            status=status,
            summary="Integration evidence must be explicit before release readiness.",
        ),
        _evidence_check(
            company_root=company_root,
            check_id="code_review",
            relative_path="review/code-review.md",
            status=status,
            summary="Code-review evidence must be explicit before release readiness.",
        ),
        _evidence_check(
            company_root=company_root,
            check_id="security_review",
            relative_path="review/security-review.md",
            status=status,
            summary="Security evidence must be explicit before release readiness.",
        ),
        _evidence_check(
            company_root=company_root,
            check_id="architecture_review",
            relative_path="review/architecture-review.md",
            status=status,
            summary="Architecture evidence must be explicit before release readiness.",
        ),
        _evidence_check(
            company_root=company_root,
            check_id="qa_verdict",
            relative_path="review/qa-verdict.md",
            status=status,
            summary="QA verification evidence must be explicit before release readiness.",
        ),
        _evidence_check(
            company_root=company_root,
            check_id="review_gate",
            relative_path="review/review-gate.json",
            status=status,
            summary="Review gate verdict must be explicit before release readiness.",
        ),
        _evidence_check(
            company_root=company_root,
            check_id="release_summary",
            relative_path="release/release-summary.md",
            status=status,
            summary="Release summary must cite concrete run evidence.",
        ),
        _evidence_check(
            company_root=company_root,
            check_id="memory_closeout",
            relative_path="memory-closeout.md",
            status=status,
            summary="Memory closeout must remain curated and evidence-backed.",
        ),
    )
    return checks


def _evidence_check(
    company_root: Path,
    check_id: str,
    relative_path: str,
    status: CompanyRunEvidenceCheckStatus,
    summary: str,
) -> CompanyRunEvidenceCheck:
    """Build one evidence check with an absolute artifact path.

    Args:
        company_root [Path]: Directory that owns company-run artifacts.
        check_id [str]: Stable check id.
        relative_path [str]: Company-run-relative artifact path.
        status [CompanyRunEvidenceCheckStatus]: Check status.
        summary [str]: Human-readable check summary.

    Returns:
        CompanyRunEvidenceCheck: Typed check payload.
    """
    check = CompanyRunEvidenceCheck(
        check_id=check_id,
        status=status,
        evidence_path=str(company_root / relative_path),
        summary=summary,
    )
    return check


def _evidence_check_status(
    team_status: CompanyRunTeamLaunchStatus,
) -> CompanyRunEvidenceCheckStatus:
    """Map Team status to evidence-check status.

    Args:
        team_status [CompanyRunTeamLaunchStatus]: Team launch outcome.

    Returns:
        CompanyRunEvidenceCheckStatus: Pass only for completed Team evidence,
        otherwise blocked.
    """
    if team_status == CompanyRunTeamLaunchStatus.COMPLETED:
        return CompanyRunEvidenceCheckStatus.PASS
    return CompanyRunEvidenceCheckStatus.BLOCKED


def _checks_passed(checks: tuple[CompanyRunEvidenceCheck, ...]) -> bool:
    """Return whether every explicit evidence check passed.

    Args:
        checks [tuple[CompanyRunEvidenceCheck, ...]]: Evidence checks.

    Returns:
        bool: True when every check status is `pass`.
    """
    return all(check.status == CompanyRunEvidenceCheckStatus.PASS for check in checks)


def _post_team_blockers(
    team_status: CompanyRunTeamLaunchStatus,
) -> tuple[str, ...]:
    """Return honest blockers for post-Team gates.

    Args:
        team_status [CompanyRunTeamLaunchStatus]: Team launch outcome.

    Returns:
        tuple[str, ...]: Empty only when Team completed.
    """
    if team_status == CompanyRunTeamLaunchStatus.COMPLETED:
        return ()
    return ("OMX Team follow-up is required before release can be claimed.",)


def _post_team_verdict_note(
    gate: str,
    verdict: str,
    blockers: tuple[str, ...],
) -> str:
    """Render a concise gate note with blunt blocker wording.

    Args:
        gate [str]: Gate label.
        verdict [str]: Persisted verdict.
        blockers [tuple[str, ...]]: Current blockers.

    Returns:
        str: Gate note.
    """
    if blockers:
        return f"{gate}: BLOCKED - {'; '.join(blockers)}"
    return f"{gate}: {verdict}"


def _blocker_text(blockers: tuple[str, ...]) -> str:
    """Render blockers for markdown evidence artifacts.

    Args:
        blockers [tuple[str, ...]]: Current blockers.

    Returns:
        str: Markdown-ready blocker text.
    """
    if not blockers:
        return "Blockers: none recorded."
    blocker_items = "\n".join(f"- {blocker}" for blocker in blockers)
    return f"Release readiness: BLOCKED\n\nBlockers:\n{blocker_items}"
