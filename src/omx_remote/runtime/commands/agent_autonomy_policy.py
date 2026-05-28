from omx_remote.schemas.commands.command_execution_schemas import (
    CommandAutonomyDecision,
    CommandAutonomyDecisionKind,
    CommandAutonomyMode,
)
from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandExecutionPlan,
    CommandRisk,
)


def _risk_safeguards(risk: CommandRisk) -> tuple[str, ...]:
    """Return required safeguards for one command risk class.

    Args:
        risk: See function signature.

    Returns:
        See function return annotation."""
    common_safeguards: tuple[str, ...] = (
        "record_run",
        "capture_stdout_stderr",
        "artifact_check",
    )
    if risk == CommandRisk.READ_ONLY:
        safeguards = common_safeguards
        return safeguards
    if risk == CommandRisk.EXTERNAL_NETWORK:
        safeguards = (*common_safeguards, "source_capture", "timeout")
        return safeguards
    if risk == CommandRisk.WRITES_FILES:
        safeguards = (*common_safeguards, "artifact_boundary", "secret_redaction")
        return safeguards
    if risk == CommandRisk.LONG_RUNNING:
        safeguards = (*common_safeguards, "timeout", "handoff_checkpoint")
        return safeguards

    safeguards = (*common_safeguards, "runtime_preflight", "handoff_checkpoint")
    return safeguards


def _is_recoverable_plan_blocker(reason: str) -> bool:
    """Return whether the executor can recover a planning blocker at runtime.

    Args:
        reason: See function signature.

    Returns:
        See function return annotation."""
    if not reason.startswith("Prompt file does not exist:"):
        return False
    recoverable = (
        "/.agent-remote/runs/" in reason or "\\.agent-remote\\runs\\" in reason
    )
    return recoverable


def _nonrecoverable_blockers(plan: CommandExecutionPlan) -> tuple[str, ...]:
    """Filter blockers that cannot be recovered by the execution pipeline.

    Args:
        plan: See function signature.

    Returns:
        See function return annotation."""
    blockers: tuple[str, ...] = tuple(
        reason
        for reason in plan.blocked_reasons
        if not _is_recoverable_plan_blocker(reason)
    )
    return blockers


class AgentAutonomyPolicy:
    """Agent-owned policy for allowing, blocking, retrying, or deferring work."""

    def decide(
        self,
        plan: CommandExecutionPlan,
        mode: CommandAutonomyMode = CommandAutonomyMode.AGENT,
    ) -> CommandAutonomyDecision:
        """Decide whether an actual command run may start.

        Args:
            plan: See function signature.
            mode: See function signature.

        Returns:
            See function return annotation."""
        if mode != CommandAutonomyMode.AGENT:
            decision = CommandAutonomyDecision(
                mode=mode,
                decision=CommandAutonomyDecisionKind.BLOCK,
                reason="Unsupported autonomy mode.",
                required_safeguards=(),
                blocked_reasons=(f"unsupported autonomy mode: {mode}",),
            )
            return decision

        nonrecoverable_blockers = _nonrecoverable_blockers(plan)
        if nonrecoverable_blockers:
            blocked = CommandAutonomyDecision(
                mode=mode,
                decision=CommandAutonomyDecisionKind.BLOCK,
                reason="Plan contains blockers that must be resolved before execution.",
                required_safeguards=_risk_safeguards(plan.risk),
                blocked_reasons=nonrecoverable_blockers,
            )
            return blocked

        allowed = CommandAutonomyDecision(
            mode=mode,
            decision=CommandAutonomyDecisionKind.ALLOW,
            reason="Agent autonomy policy allows execution with required safeguards.",
            required_safeguards=(
                *_risk_safeguards(plan.risk),
                *(
                    ("recover_generated_prompt_files",)
                    if len(nonrecoverable_blockers) != len(plan.blocked_reasons)
                    else ()
                ),
            ),
            blocked_reasons=(),
        )
        return allowed
