from omx_remote.shared.omx_enums.company_run_enums import (
    CompanyRunTeamLaunchBlockerSignal,
)


def team_launch_needs_workspace_handoff(output: str) -> bool:
    """Return whether Team launch failed on a dirty-worktree precondition.

    Args:
        output [str]: Combined stdout/stderr from OMX Team launch.

    Returns:
        bool: Whether the failure requires workspace cleanup before Team launch.
    """
    normalized_output = output.lower()
    requires_handoff = any(
        signal.value in normalized_output
        for signal in (
            CompanyRunTeamLaunchBlockerSignal.DIRTY_WORKTREE,
            CompanyRunTeamLaunchBlockerSignal.COMMIT_OR_STASH,
        )
    )
    return requires_handoff


def team_launch_needs_startup_handoff(output: str) -> bool:
    """Return whether Team launch reached worker startup but needs follow-up.

    Args:
        output [str]: Combined stdout/stderr from OMX Team launch.

    Returns:
        bool: Whether a startup/readiness issue requires operator follow-up.
    """
    normalized_output = output.lower()
    requires_handoff = any(
        signal.value in normalized_output
        for signal in (
            CompanyRunTeamLaunchBlockerSignal.WORKER_DID_NOT_BECOME_READY,
            CompanyRunTeamLaunchBlockerSignal.READY_PROMPT_TIMEOUT,
            CompanyRunTeamLaunchBlockerSignal.STARTUP_PROMPT_TIMEOUT,
            CompanyRunTeamLaunchBlockerSignal.WORKER_STARTUP_TIMEOUT,
            CompanyRunTeamLaunchBlockerSignal.STARTUP_TIMEOUT,
        )
    )
    return requires_handoff


def team_launch_needs_workflow_handoff(output: str) -> bool:
    """Return whether Team launch is blocked by active OMX workflow state.

    Args:
        output [str]: Combined stdout/stderr from OMX Team launch.

    Returns:
        bool: Whether conflicting active workflow modes require handoff.
    """
    normalized_output = output.lower()
    requires_handoff = any(
        signal.value in normalized_output
        for signal in (
            CompanyRunTeamLaunchBlockerSignal.LEADER_SESSION_CONFLICT,
            CompanyRunTeamLaunchBlockerSignal.ACTIVE_TEAM_EXISTS,
            CompanyRunTeamLaunchBlockerSignal.CANNOT_START_TEAM,
            CompanyRunTeamLaunchBlockerSignal.WORKFLOW_OVERLAP,
        )
    )
    return requires_handoff
