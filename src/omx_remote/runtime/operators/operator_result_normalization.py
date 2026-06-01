from omx_remote.schemas.operator_action_schemas import (
    OperatorActionResult,
    OperatorLane,
    OperatorLoopState,
    OperatorNextAction,
    OperatorRecoveryHint,
)
from omx_remote.schemas.teamwork.operator_schemas import (
    TeamOperatorDispatchOutcome,
)
from omx_remote.shared.omx_enums.teamwork_enums import (
    TeamOperatorDispatchOutcomeState,
)


def normalized_message_from_command_result(command_result) -> str:
    """Handles normalized message from command result.

    Args:
        command_result [object]: Function argument.

    Returns:
        str: Function return value.
    """
    message_source: str
    if command_result.stderr != "":
        message_source = command_result.stderr
    else:
        message_source = command_result.stdout

    normalized_message: str = message_source.strip().lower()
    return normalized_message


def build_runtime_success_result(
    lane: OperatorLane,
    action: str,
    command_result,
) -> OperatorActionResult:
    """Handles build runtime success result.

    Args:
        lane [OperatorLane]: Function argument.
        action [str]: Function argument.
        command_result [object]: Function argument.

    Returns:
        OperatorActionResult: Function return value.
    """
    next_action: OperatorNextAction
    summary: str
    recovery_hint: OperatorRecoveryHint | None
    if action == "cleanup":
        next_action = OperatorNextAction.RETRY
        summary = f"{lane} cleanup succeeded and the lane can now be retried."
        recovery_hint = OperatorRecoveryHint(
            next_action=OperatorNextAction.RETRY,
            reason="Cleanup completed, so retrying the lane is now the next safe step.",
            cleanup_first=False,
        )
    else:
        next_action = OperatorNextAction.OBSERVE
        summary = f"{lane} {action} succeeded and the lane can now be observed."
        recovery_hint = None

    result: OperatorActionResult = OperatorActionResult(
        lane=lane,
        action=action,
        loop_state=OperatorLoopState.SUCCESS,
        next_action=next_action,
        summary=summary,
        recovery_hint=recovery_hint,
        command_result=command_result,
    )
    return result


def build_runtime_failure_result(
    lane: OperatorLane,
    action: str,
    command_result,
) -> OperatorActionResult:
    """Handles build runtime failure result.

    Args:
        lane [OperatorLane]: Function argument.
        action [str]: Function argument.
        command_result [object]: Function argument.

    Returns:
        OperatorActionResult: Function return value.
    """
    normalized_message: str = normalized_message_from_command_result(command_result)

    if (
        "no resumable" in normalized_message
        or "no ralph state found" in normalized_message
    ):
        recovery_hint = OperatorRecoveryHint(
            next_action=OperatorNextAction.LAUNCH,
            reason="No resumable runtime state exists, so a fresh launch is required.",
        )
        result = OperatorActionResult(
            lane=lane,
            action=action,
            loop_state=OperatorLoopState.NO_RESUMABLE_STATE_FAILURE,
            next_action=OperatorNextAction.LAUNCH,
            summary=f"{lane} {action} could not resume because no resumable state exists.",
            recovery_hint=recovery_hint,
            command_result=command_result,
        )
        return result

    if "no ultrawork state found" in normalized_message:
        recovery_hint = OperatorRecoveryHint(
            next_action=OperatorNextAction.LAUNCH,
            reason="No resumable runtime state exists, so a fresh launch is required.",
        )
        result = OperatorActionResult(
            lane=lane,
            action=action,
            loop_state=OperatorLoopState.NO_RESUMABLE_STATE_FAILURE,
            next_action=OperatorNextAction.LAUNCH,
            summary=f"{lane} {action} could not resume because no resumable state exists.",
            recovery_hint=recovery_hint,
            command_result=command_result,
        )
        return result

    if (
        "existing resumable" in normalized_message
        or "cleanup-stale" in normalized_message
    ):
        recovery_hint = OperatorRecoveryHint(
            next_action=OperatorNextAction.CLEANUP,
            reason="Existing or stale runtime state blocks the lane, so cleanup is required before retrying.",
            cleanup_first=True,
        )
        result = OperatorActionResult(
            lane=lane,
            action=action,
            loop_state=OperatorLoopState.STALE_STATE_FAILURE,
            next_action=OperatorNextAction.CLEANUP,
            summary=f"{lane} {action} is blocked by stale or already-resumable state.",
            recovery_hint=recovery_hint,
            command_result=command_result,
        )
        return result

    if "dirty" in normalized_message and "workspace" in normalized_message:
        recovery_hint = OperatorRecoveryHint(
            next_action=OperatorNextAction.CLEANUP,
            reason="A dirty workspace blocks the lane, so workspace cleanup is required before retrying.",
            cleanup_first=True,
        )
        result = OperatorActionResult(
            lane=lane,
            action=action,
            loop_state=OperatorLoopState.DIRTY_WORKSPACE_FAILURE,
            next_action=OperatorNextAction.CLEANUP,
            summary=f"{lane} {action} is blocked by a dirty workspace.",
            recovery_hint=recovery_hint,
            command_result=command_result,
        )
        return result

    if "approval" in normalized_message:
        recovery_hint = OperatorRecoveryHint(
            next_action=OperatorNextAction.ESCALATE,
            reason="Approval is required before the lane can continue.",
        )
        result = OperatorActionResult(
            lane=lane,
            action=action,
            loop_state=OperatorLoopState.BLOCKED_APPROVAL_NEEDED,
            next_action=OperatorNextAction.ESCALATE,
            summary=f"{lane} {action} is blocked on approval.",
            recovery_hint=recovery_hint,
            command_result=command_result,
        )
        return result

    recovery_hint = OperatorRecoveryHint(
        next_action=OperatorNextAction.ESCALATE,
        reason="The lane failed without a known recovery pattern, so escalation is the safest next step.",
    )
    result = OperatorActionResult(
        lane=lane,
        action=action,
        loop_state=OperatorLoopState.TERMINAL_FAILURE,
        next_action=OperatorNextAction.ESCALATE,
        summary=f"{lane} {action} failed without a standardized recovery path.",
        recovery_hint=recovery_hint,
        command_result=command_result,
    )
    return result


def normalize_runtime_command_result(
    lane: OperatorLane,
    action: str,
    command_result,
) -> OperatorActionResult:
    """Handles normalize runtime command result.

    Args:
        lane [OperatorLane]: Function argument.
        action [str]: Function argument.
        command_result [object]: Function argument.

    Returns:
        OperatorActionResult: Function return value.
    """
    if command_result.exit_code == 0:
        result: OperatorActionResult = build_runtime_success_result(
            lane=lane,
            action=action,
            command_result=command_result,
        )
        return result

    result = build_runtime_failure_result(
        lane=lane,
        action=action,
        command_result=command_result,
    )
    return result


def normalize_team_dispatch_result(
    action: str,
    dispatch_result: TeamOperatorDispatchOutcome,
    unverified_loop_state: OperatorLoopState,
    unverified_next_action: OperatorNextAction,
) -> OperatorActionResult:
    """Handles normalize team dispatch result.

    Args:
        action [str]: Function argument.
        dispatch_result [TeamOperatorDispatchOutcome]: Function argument.
        unverified_loop_state [OperatorLoopState]: Function argument.
        unverified_next_action [OperatorNextAction]: Function argument.

    Returns:
        OperatorActionResult: Function return value.
    """
    if dispatch_result.outcome == TeamOperatorDispatchOutcomeState.ACCEPTED:
        accepted_result: OperatorActionResult = OperatorActionResult(
            lane=OperatorLane.TEAM,
            action=action,
            loop_state=OperatorLoopState.SUCCESS,
            next_action=OperatorNextAction.OBSERVE,
            summary=f"team {action} completed and the lane can now be observed.",
            recovery_hint=None,
            command_result=dispatch_result.command_result,
        )
        return accepted_result

    if (
        dispatch_result.outcome
        == TeamOperatorDispatchOutcomeState.ACCEPTED_BUT_UNVERIFIED
    ):
        recovery_hint = OperatorRecoveryHint(
            next_action=unverified_next_action,
            reason=dispatch_result.reason,
        )
        unverified_result: OperatorActionResult = OperatorActionResult(
            lane=OperatorLane.TEAM,
            action=action,
            loop_state=unverified_loop_state,
            next_action=unverified_next_action,
            summary=f"team {action} was accepted by OMX but still needs follow-up confirmation.",
            recovery_hint=recovery_hint,
            command_result=dispatch_result.command_result,
        )
        return unverified_result

    recovery_hint = OperatorRecoveryHint(
        next_action=OperatorNextAction.ESCALATE,
        reason=dispatch_result.reason,
    )
    failed_result: OperatorActionResult = OperatorActionResult(
        lane=OperatorLane.TEAM,
        action=action,
        loop_state=OperatorLoopState.TERMINAL_FAILURE,
        next_action=OperatorNextAction.ESCALATE,
        summary=f"team {action} failed and needs escalation.",
        recovery_hint=recovery_hint,
        command_result=dispatch_result.command_result,
    )
    return failed_result
