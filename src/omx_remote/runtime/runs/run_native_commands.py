from omx_remote.runtime.commands.command_output_redaction import redact_argv
from omx_remote.schemas.commands.command_recipe_schemas import CommandExecutionPlan
from omx_remote.schemas.runs.run_record_schemas import RunNativeCommand


def collect_run_native_commands(
    plan: CommandExecutionPlan,
) -> tuple[RunNativeCommand, ...]:
    """Collect redacted native command previews from a command execution plan.

    Args:
        plan [CommandExecutionPlan]: Command execution plan to inspect.

    Returns:
        tuple[RunNativeCommand, ...]: Redacted native command previews.
    """
    commands: tuple[RunNativeCommand, ...] = tuple(
        RunNativeCommand(index=step.index, argv=redact_argv(step.native_argv))
        for step in plan.steps
        if step.native_argv
    )
    return commands
