from __future__ import annotations

from dataclasses import dataclass

from omx_remote.runtime.company_run.team.team_evidence import (
    TeamStateCompletionEvidence,
)
from omx_remote.shared.omx_enums.company_run_enums import CompanyRunTeamLaunchStatus


@dataclass(frozen=True)
class CompanyRunTeamCompletionDecision:
    """Company-run Team status decision after native await/status reconciliation."""

    status: CompanyRunTeamLaunchStatus
    note: str


def reconcile_team_completion_evidence(
    await_clean: bool,
    completion_evidence: TeamStateCompletionEvidence,
) -> CompanyRunTeamCompletionDecision:
    """Decide final company-run Team status from await and Team state evidence.

    Args:
        await_clean [bool]: Whether native `omx team await` exited cleanly.
        completion_evidence [TeamStateCompletionEvidence]: Status/list-task proof.

    Returns:
        CompanyRunTeamCompletionDecision: Completed or follow-up decision.
    """
    if completion_evidence.complete:
        decision = CompanyRunTeamCompletionDecision(
            status=CompanyRunTeamLaunchStatus.COMPLETED,
            note=_completed_note(
                await_clean=await_clean,
                completion_evidence=completion_evidence,
            ),
        )
        return decision
    if completion_evidence.terminal:
        decision = CompanyRunTeamCompletionDecision(
            status=CompanyRunTeamLaunchStatus.REQUIRES_AGENT_ACTION,
            note=_terminal_missing_note(
                await_clean=await_clean,
                completion_evidence=completion_evidence,
            ),
        )
        return decision
    decision = CompanyRunTeamCompletionDecision(
        status=CompanyRunTeamLaunchStatus.REQUIRES_AGENT_ACTION,
        note=_incomplete_note(
            await_clean=await_clean,
            completion_evidence=completion_evidence,
        ),
    )
    return decision


def _completed_note(
    await_clean: bool,
    completion_evidence: TeamStateCompletionEvidence,
) -> str:
    """Render a completed-Team note.

    Args:
        await_clean [bool]: Whether await exited cleanly.
        completion_evidence [TeamStateCompletionEvidence]: Completion proof.

    Returns:
        str: Human-readable Team completion note.
    """
    if await_clean:
        note = (
            "OMX Team launched, await returned cleanly, and Team state shows all "
            f"tasks completed. {completion_evidence.detail}"
        )
        return note
    note = (
        "OMX Team await did not exit cleanly, but Team state shows all tasks "
        f"completed. {completion_evidence.detail}"
    )
    return note


def _terminal_missing_note(
    await_clean: bool,
    completion_evidence: TeamStateCompletionEvidence,
) -> str:
    """Render a terminal missing-state note.

    Args:
        await_clean [bool]: Whether await exited cleanly.
        completion_evidence [TeamStateCompletionEvidence]: Terminal evidence.

    Returns:
        str: Human-readable terminal missing-state note.
    """
    if await_clean:
        note = (
            "OMX Team await returned cleanly, but Team status is now missing; "
            "treat this as cleanup/stale notification evidence rather than "
            f"actionable worker work. {completion_evidence.detail}"
        )
        return note
    note = (
        "OMX Team await did not exit cleanly and Team status is now missing; "
        "treat this as cleanup/stale notification evidence rather than actionable "
        f"worker work. {completion_evidence.detail}"
    )
    return note


def _incomplete_note(
    await_clean: bool,
    completion_evidence: TeamStateCompletionEvidence,
) -> str:
    """Render an incomplete-Team note.

    Args:
        await_clean [bool]: Whether await exited cleanly.
        completion_evidence [TeamStateCompletionEvidence]: Incomplete evidence.

    Returns:
        str: Human-readable incomplete-Team note.
    """
    if await_clean:
        note = (
            "OMX Team await returned cleanly, but Team state does not show "
            f"completed worker output. {completion_evidence.detail}"
        )
        return note
    note = (
        "OMX Team launch succeeded, but await needs follow-up; Team state does "
        f"not show completed worker output. {completion_evidence.detail}"
    )
    return note
