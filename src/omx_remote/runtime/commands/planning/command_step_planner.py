from pathlib import Path

from omx_remote.runtime.agents.agent_config_loader import load_agent_config
from omx_remote.runtime.commands.rendering.command_step_rendering import (
    apply_task_placeholder,
    effective_codex_sandbox,
    native_step_argv,
    prompt_file_hash,
    resolve_command_path,
    resolve_expected_artifacts,
)
from omx_remote.schemas.agents.agent_config_schemas import AgentConfigSet
from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandExecutionPlan,
    CommandPlanStep,
    CommandRecipe,
    CommandRisk,
    CommandSource,
    CommandStep,
    CommandStepCommand,
)
from omx_remote.schemas.commands.command_runtime_option_schemas import (
    CommandRuntimeOptions,
)


def _agent_blockers(
    step: CommandStep,
    agent_config: AgentConfigSet,
) -> tuple[str, ...]:
    """Detect agent-reference blockers for one step.

    Args:
        step [CommandStep]: Step to inspect.
        agent_config [AgentConfigSet]: Loaded repo agent config.

    Returns:
        tuple[str, ...]: Agent-related blockers.
    """
    if step.agent is None:
        no_blockers: tuple[str, ...] = ()
        return no_blockers

    agent = agent_config.find_agent(step.agent)
    if agent is None:
        missing_agent_blockers = (f"No agent named {step.agent} is configured.",)
        return missing_agent_blockers
    if not agent.enabled:
        disabled_agent_blockers = (f"Agent {step.agent} is disabled.",)
        return disabled_agent_blockers

    no_blockers = ()
    return no_blockers


def _mcp_blockers(step: CommandStep) -> tuple[str, ...]:
    """Detect missing MCP tool references for one step.

    Args:
        step [CommandStep]: Step to inspect.

    Returns:
        tuple[str, ...]: MCP-related blockers.
    """
    if step.command != CommandStepCommand.MCP_TOOL:
        no_blockers: tuple[str, ...] = ()
        return no_blockers

    blockers: list[str] = []
    if step.mcp_server is None:
        blockers.append("MCP tool step requires mcp_server.")
    if step.mcp_tool is None:
        blockers.append("MCP tool step requires mcp_tool.")

    mcp_blockers: tuple[str, ...] = tuple(blockers)
    return mcp_blockers


def _prompt_file_metadata(
    cwd: str | Path | None,
    step: CommandStep,
) -> tuple[str | None, bool | None, str | None, tuple[str, ...]]:
    """Resolve prompt-file metadata for one step.

    Args:
        cwd [str | Path | None]: Base working directory for relative paths.
        step [CommandStep]: Step to inspect.

    Returns:
        tuple[str | None, bool | None, str | None, tuple[str, ...]]: Prompt path, existence, hash, blockers.
    """
    prompt_path_text: str | None = step.prompt_file or step.brief_file
    if prompt_path_text is None:
        metadata = (None, None, None, ())
        return metadata

    prompt_path: Path = resolve_command_path(cwd, prompt_path_text)
    prompt_exists: bool = prompt_path.exists()
    prompt_sha256: str | None = prompt_file_hash(prompt_path)
    blockers: tuple[str, ...] = ()
    generated_brief_artifact = (
        step.prompt_file is None
        and step.brief_file is not None
        and step.brief_file in step.expected_artifacts
    )
    if not prompt_exists and not generated_brief_artifact:
        blockers = (f"Prompt file does not exist: {prompt_path}",)

    metadata = (str(prompt_path), prompt_exists, prompt_sha256, blockers)
    return metadata


def _build_plan_step(
    index: int,
    cwd: str | Path | None,
    step: CommandStep,
    recipe_risk: CommandRisk,
    agent_config: AgentConfigSet,
    task_text: str | None,
    runtime_options: CommandRuntimeOptions | None,
) -> CommandPlanStep:
    """Build one dry-run plan step.

    Args:
        index [int]: One-based step index.
        cwd [str | Path | None]: Base working directory for relative paths.
        step [CommandStep]: Recipe step to render.
        recipe_risk [CommandRisk]: Parent recipe risk.
        agent_config [AgentConfigSet]: Loaded repo agent config.
        task_text [str | None]: Optional caller-supplied task text.
        runtime_options [CommandRuntimeOptions | None]: Optional Codex runtime controls.

    Returns:
        CommandPlanStep: Dry-run plan step.
    """
    prompt_file, prompt_exists, prompt_sha256, prompt_blockers = _prompt_file_metadata(
        cwd,
        step,
    )
    blockers: tuple[str, ...] = (
        *prompt_blockers,
        *_agent_blockers(step, agent_config),
        *_mcp_blockers(step),
    )
    plan_step = CommandPlanStep(
        index=index,
        command=step.command,
        agent=step.agent,
        native_argv=native_step_argv(
            cwd=cwd,
            step=step,
            task_text=task_text,
            runtime_options=runtime_options,
        ),
        codex_search=step.codex_search,
        codex_sandbox=effective_codex_sandbox(step),
        prompt_file=prompt_file,
        prompt_exists=prompt_exists,
        prompt_sha256=prompt_sha256,
        inline_prompt=apply_task_placeholder(step.inline_prompt, task_text),
        mcp_server=step.mcp_server,
        mcp_tool=step.mcp_tool,
        mcp_arguments=step.mcp_arguments,
        expected_artifacts=resolve_expected_artifacts(cwd, step),
        role_lanes=step.role_lanes,
        risk=recipe_risk,
        blocked_reasons=blockers,
    )
    return plan_step


def build_command_execution_plan(
    recipe: CommandRecipe,
    cwd: str | Path | None = None,
    dry_run: bool = True,
    task_text: str | None = None,
    runtime_options: CommandRuntimeOptions | None = None,
) -> CommandExecutionPlan:
    """Build an inspectable command execution plan.

    Args:
        recipe [CommandRecipe]: Command recipe to plan.
        cwd [str | Path | None]: Base working directory for relative paths.
        dry_run [bool]: Whether the plan is dry-run only.
        task_text [str | None]: Optional caller-supplied task text.
        runtime_options [CommandRuntimeOptions | None]: Optional Codex runtime controls.

    Returns:
        CommandExecutionPlan: Typed dry-run execution plan.
    """
    agent_config: AgentConfigSet = load_agent_config(cwd=cwd)
    steps: tuple[CommandPlanStep, ...] = tuple(
        _build_plan_step(
            index,
            cwd,
            step,
            recipe.risk,
            agent_config,
            task_text,
            runtime_options,
        )
        for index, step in enumerate(recipe.steps, start=1)
    )
    blocked_reasons: tuple[str, ...] = tuple(
        reason for step in steps for reason in step.blocked_reasons
    )
    plan = CommandExecutionPlan(
        command_id=recipe.display_id,
        qualified_id=recipe.display_qualified_id,
        source=recipe.source,
        namespace=recipe.namespace,
        category=recipe.category,
        description=recipe.description,
        risk=recipe.risk,
        dry_run=dry_run,
        runtime_options=runtime_options,
        steps=steps,
        blocked_reasons=blocked_reasons,
    )
    return plan


def build_one_off_prompt_recipe(
    provider: str,
    prompt_file: str | Path | None,
    inline_prompt: str | None,
) -> CommandRecipe:
    """Build a one-off prompt recipe from CLI inputs.

    Args:
        provider [str]: Provider selected by the caller.
        prompt_file [str | Path | None]: Optional prompt file path.
        inline_prompt [str | None]: Optional inline prompt text.

    Returns:
        CommandRecipe: One-off recipe suitable for dry-run planning.
    """
    if provider != "codex":
        raise ValueError(
            "one-off prompt dry-run currently supports provider=codex only"
        )
    if prompt_file is None and inline_prompt is None:
        raise ValueError(
            "one-off prompt dry-run requires --prompt-file or --inline-prompt"
        )

    step = CommandStep(
        command=CommandStepCommand.CODEX_EXEC,
        prompt_file=None if prompt_file is None else str(prompt_file),
        inline_prompt=inline_prompt,
    )
    recipe = CommandRecipe(
        id="one-off-prompt",
        source=CommandSource.ONE_OFF,
        description="One-off prompt dry-run command.",
        risk=CommandRisk.READ_ONLY,
        steps=(step,),
    )
    return recipe
