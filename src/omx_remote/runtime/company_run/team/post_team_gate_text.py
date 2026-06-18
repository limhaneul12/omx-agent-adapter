from __future__ import annotations

from omx_remote.shared.omx_enums.company_run_enums import CompanyRunTeamLaunchStatus


def post_team_markdown_files(
    team_status: CompanyRunTeamLaunchStatus,
    blockers: tuple[str, ...],
) -> dict[str, str]:
    """Return post-Team markdown artifact templates.

    Args:
        team_status [CompanyRunTeamLaunchStatus]: Team launch outcome.
        blockers [tuple[str, ...]]: Current Team-derived blockers.

    Returns:
        dict[str, str]: Company-run-relative artifact path to markdown body.
    """
    blocker_text = post_team_blocker_text(blockers=blockers)
    team_context = team_context_text(team_status=team_status)
    evidence_context = evidence_context_text(team_status=team_status)
    files = {
        "team/team-sync.md": (
            f"{team_context}\n\n{evidence_context}\n\n{blocker_text}"
        ),
        "team/integration-plan.md": (
            "Integration plan preserves worker ownership, handoff boundaries, "
            f"and verification order.\n\n{blocker_text}"
        ),
        "review/code-review.md": (
            "Code review gate requires explicit leader synthesis of worker "
            f"results before release readiness.\n\n{blocker_text}"
        ),
        "review/security-review.md": (
            "Security review gate requires explicit leader synthesis of worker "
            f"security evidence before release readiness.\n\n{blocker_text}"
        ),
        "review/architecture-review.md": (
            "Architecture review gate requires explicit leader synthesis of "
            f"integration evidence before release readiness.\n\n{blocker_text}"
        ),
        "review/qa-verdict.md": (
            "QA gate requires explicit leader synthesis of verification evidence.\n\n"
            f"{blocker_text}"
        ),
        "release/release-summary.md": (
            f"{team_context}\n\nRelease summary recorded from company-run evidence; "
            f"do not claim release readiness while blockers remain.\n\n{blocker_text}"
        ),
        "memory-closeout.md": (
            "Alexandria MCP closeout point recorded for curated memory save "
            f"after verified release evidence.\n\n{blocker_text}"
        ),
    }
    return files


def team_context_text(team_status: CompanyRunTeamLaunchStatus) -> str:
    """Render Team execution status for markdown artifacts.

    Args:
        team_status [CompanyRunTeamLaunchStatus]: Team launch outcome.

    Returns:
        str: Team execution context.
    """
    if team_status == CompanyRunTeamLaunchStatus.COMPLETED:
        context = "Team execution: COMPLETE"
        return context
    context = "Team execution: FOLLOW-UP REQUIRED"
    return context


def evidence_context_text(team_status: CompanyRunTeamLaunchStatus) -> str:
    """Render post-Team evidence boundary context.

    Args:
        team_status [CompanyRunTeamLaunchStatus]: Team launch outcome.

    Returns:
        str: Evidence boundary text.
    """
    if team_status == CompanyRunTeamLaunchStatus.COMPLETED:
        context = (
            "Worker execution completed, but release readiness still requires "
            "leader-owned integration, review, security, architecture, and QA "
            "synthesis from concrete worker results."
        )
        return context
    context = "Worker execution is not complete; inspect Team state before release work."
    return context


def post_team_blocker_text(blockers: tuple[str, ...]) -> str:
    """Render blockers for markdown evidence artifacts.

    Args:
        blockers [tuple[str, ...]]: Current blockers.

    Returns:
        str: Markdown-ready blocker text.
    """
    if not blockers:
        text = "Blockers: none recorded."
        return text
    blocker_items = "\n".join(f"- {blocker}" for blocker in blockers)
    text = f"Release readiness: BLOCKED\n\nBlockers:\n{blocker_items}"
    return text
