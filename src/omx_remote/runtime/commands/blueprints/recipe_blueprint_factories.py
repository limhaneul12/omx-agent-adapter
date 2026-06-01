from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandStep,
    CommandStepCommand,
)
from omx_remote.schemas.commands.command_role_schemas import (
    CommandRoleExecution,
    CommandRoleLane,
)


def role_lane(
    lane_id: str,
    execution: CommandRoleExecution,
    purpose: str,
    artifact: str | None = None,
    approval_required: bool = False,
) -> CommandRoleLane:
    """Build one declared workflow role lane.

    Args:
        lane_id [str]: Stable role lane identifier.
        execution [CommandRoleExecution]: Execution ownership class.
        purpose [str]: Human-readable role purpose.
        artifact [str | None]: Optional artifact owned by the lane.
        approval_required [bool]: Whether this lane gates approval.

    Returns:
        CommandRoleLane: Typed role lane contract.
    """
    lane = CommandRoleLane(
        id=lane_id,
        execution=execution,
        purpose=purpose,
        artifact=artifact,
        approval_required=approval_required,
    )
    return lane


def codex_step(
    prompt: str,
    output_last_message: str | None = None,
    expected_artifacts: tuple[str, ...] = (),
    search: bool = False,
    prompt_file: str | None = None,
    agent: str | None = None,
    role_lanes: tuple[CommandRoleLane, ...] = (),
) -> CommandStep:
    """Build a read-only Codex exec recipe step.

    Args:
        prompt [str]: Inline task prompt sent with the step.
        output_last_message [str | None]: Optional Codex final-message artifact path.
        expected_artifacts [tuple[str, ...]]: Additional artifacts required after the step.
        search [bool]: Whether the step uses Codex live search.
        prompt_file [str | None]: Optional prompt template path.
        agent [str | None]: Optional configured agent id.
        role_lanes [tuple[CommandRoleLane, ...]]: Specialist role lanes for the step.

    Returns:
        CommandStep: Typed Codex command step.
    """
    step = CommandStep(
        command=CommandStepCommand.CODEX_EXEC,
        agent=agent,
        codex_search=search,
        codex_sandbox="read-only",
        prompt_file=prompt_file,
        inline_prompt=prompt,
        output_last_message=output_last_message,
        expected_artifacts=expected_artifacts,
        role_lanes=role_lanes,
    )
    return step


def prompt_step(
    prompt: str,
    expected_artifacts: tuple[str, ...] = (),
    prompt_file: str | None = None,
    role_lanes: tuple[CommandRoleLane, ...] = (),
) -> CommandStep:
    """Build a prompt-only recipe step.

    Args:
        prompt [str]: Handoff prompt text.
        expected_artifacts [tuple[str, ...]]: Artifacts to materialize for the handoff.
        prompt_file [str | None]: Optional prompt template path.
        role_lanes [tuple[CommandRoleLane, ...]]: Specialist role lanes for the handoff.

    Returns:
        CommandStep: Typed prompt-only command step.
    """
    step = CommandStep(
        command=CommandStepCommand.PROMPT_ONLY,
        prompt_file=prompt_file,
        inline_prompt=prompt,
        expected_artifacts=expected_artifacts,
        role_lanes=role_lanes,
    )
    return step


def local_step(
    argv: tuple[str, ...],
    role_lanes: tuple[CommandRoleLane, ...] = (),
) -> CommandStep:
    """Build a local command preview step.

    Args:
        argv [tuple[str, ...]]: Local command argv preview.
        role_lanes [tuple[CommandRoleLane, ...]]: Evidence roles for the step.

    Returns:
        CommandStep: Typed local command step.
    """
    step = CommandStep(
        command=CommandStepCommand.LOCAL,
        argv=argv,
        role_lanes=role_lanes,
    )
    return step
