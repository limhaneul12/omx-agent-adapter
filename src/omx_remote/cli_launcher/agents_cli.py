from pathlib import Path

import orjson
import typer
from pydantic import ValidationError

from omx_remote.runtime.agents.agent_config_loader import (
    AgentConfigLoadError,
    load_agent_config,
)
from omx_remote.runtime.agents.codex_agent_materialization_plan import (
    build_codex_agent_materialization_plan,
)
from omx_remote.runtime.agents.codex_agent_materializer import (
    apply_codex_agent_materialization,
    read_codex_agent_materialization_status,
)
from omx_remote.schemas.agents.agent_config_schemas import (
    AgentConfig,
    AgentConfigSet,
    AgentListResult,
    AgentShowResult,
    AgentValidationResult,
)
from omx_remote.schemas.agents.codex_agent_materialization_schemas import (
    CodexAgentMaterializationApplyResult,
    CodexAgentMaterializationPlan,
    CodexAgentMaterializationStatus,
)

agents_app = typer.Typer(
    help="Validate and inspect repo-local TOML subagent configuration.",
    add_completion=False,
)


def _format_error_payload(error: Exception, config_path: str | None = None) -> str:
    """Format one CLI error as JSON.

    Args:
        error [Exception]: Error raised while loading or validating config.
        config_path [str | None]: Optional config path to include.

    Returns:
        str: JSON error payload.
    """
    payload: dict[str, object] = {"valid": False, "error": str(error)}
    if config_path is not None:
        payload["config_path"] = config_path
    error_payload: str = orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode()
    return error_payload


def _format_agents_human_table(agents: tuple[AgentConfig, ...]) -> str:
    """Format configured agents for humans.

    Args:
        agents [tuple[AgentConfig, ...]]: Agent configs to render.

    Returns:
        str: Human-readable table-like output.
    """
    if not agents:
        empty_summary: str = "No agents configured."
        return empty_summary

    lines: list[str] = []
    for agent in agents:
        enabled_text: str = "enabled" if agent.enabled else "disabled"
        lines.append(
            f"{agent.id}\t{enabled_text}\t{agent.provider}\t{agent.role}\t{agent.model}"
        )
    table_text: str = "\n".join(lines)
    return table_text


def _build_list_result(
    config: AgentConfigSet,
    enabled_only: bool,
) -> AgentListResult:
    """Build typed list output from a loaded config.

    Args:
        config [AgentConfigSet]: Loaded agent config.
        enabled_only [bool]: Whether disabled agents should be omitted.

    Returns:
        AgentListResult: Typed list output.
    """
    listed_agents: tuple[AgentConfig, ...] = (
        config.enabled_agents if enabled_only else config.agents
    )
    enabled_count: int = len(config.enabled_agents)
    disabled_count: int = len(config.agents) - enabled_count
    list_result = AgentListResult(
        config_path=config.config_path,
        agents=listed_agents,
        enabled_count=enabled_count,
        disabled_count=disabled_count,
        warnings=config.warnings,
    )
    return list_result


@agents_app.command("list")
def agents_list(
    cwd: Path = typer.Option(
        Path("."),
        "--cwd",
        help="Repository root used to resolve .agent-remote.toml.",
    ),
    config_path: Path | None = typer.Option(
        None,
        "--config",
        help="Optional agent config path override, relative to --cwd when not absolute.",
    ),
    enabled_only: bool = typer.Option(
        False,
        "--enabled-only",
        help="Only list enabled agents.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print the typed agent list as JSON.",
    ),
) -> None:
    """List TOML-defined subagents.

    Args:
        cwd [Path]: Repository root used for config resolution.
        config_path [Path | None]: Optional config path override.
        enabled_only [bool]: Whether disabled agents should be omitted.
        json_output [bool]: Whether to print JSON.
    """
    try:
        config: AgentConfigSet = load_agent_config(cwd=cwd, config_path=config_path)
        result: AgentListResult = _build_list_result(config, enabled_only)
    except (AgentConfigLoadError, ValidationError, ValueError) as error:
        if json_output:
            typer.echo(_format_error_payload(error))
        else:
            typer.echo(str(error))
        raise typer.Exit(code=2) from error

    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        return

    typer.echo(_format_agents_human_table(result.agents))
    for warning in result.warnings:
        typer.echo(f"warning: {warning}")


@agents_app.command("show")
def agents_show(
    agent_id: str = typer.Argument(..., help="Configured agent id to show."),
    cwd: Path = typer.Option(
        Path("."),
        "--cwd",
        help="Repository root used to resolve .agent-remote.toml.",
    ),
    config_path: Path | None = typer.Option(
        None,
        "--config",
        help="Optional agent config path override, relative to --cwd when not absolute.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print the typed agent result as JSON.",
    ),
) -> None:
    """Show one TOML-defined subagent.

    Args:
        agent_id [str]: Configured agent id to show.
        cwd [Path]: Repository root used for config resolution.
        config_path [Path | None]: Optional config path override.
        json_output [bool]: Whether to print JSON.
    """
    try:
        config: AgentConfigSet = load_agent_config(cwd=cwd, config_path=config_path)
        agent: AgentConfig | None = config.find_agent(agent_id)
        if agent is None:
            raise ValueError(f"No agent named {agent_id} was found in {config.config_path}.")
        result = AgentShowResult(
            config_path=config.config_path,
            agent=agent,
            warnings=config.warnings,
        )
    except (AgentConfigLoadError, ValidationError, ValueError) as error:
        if json_output:
            typer.echo(_format_error_payload(error))
        else:
            typer.echo(str(error))
        raise typer.Exit(code=2) from error

    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        return

    typer.echo(_format_agents_human_table((result.agent,)))
    for warning in result.warnings:
        typer.echo(f"warning: {warning}")


@agents_app.command("validate")
def agents_validate(
    cwd: Path = typer.Option(
        Path("."),
        "--cwd",
        help="Repository root used to resolve .agent-remote.toml.",
    ),
    config_path: Path | None = typer.Option(
        None,
        "--config",
        help="Optional agent config path override, relative to --cwd when not absolute.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print the typed validation result as JSON.",
    ),
) -> None:
    """Validate TOML-defined subagents.

    Args:
        cwd [Path]: Repository root used for config resolution.
        config_path [Path | None]: Optional config path override.
        json_output [bool]: Whether to print JSON.
    """
    try:
        config: AgentConfigSet = load_agent_config(cwd=cwd, config_path=config_path)
    except (AgentConfigLoadError, ValidationError, ValueError) as error:
        if json_output:
            typer.echo(_format_error_payload(error))
        else:
            typer.echo(str(error))
        raise typer.Exit(code=2) from error

    result = AgentValidationResult(
        valid=True,
        config_path=config.config_path,
        agent_count=len(config.agents),
        warnings=config.warnings,
    )
    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        return

    typer.echo(f"valid: {result.valid}")
    typer.echo(f"agent_count: {result.agent_count}")
    for warning in result.warnings:
        typer.echo(f"warning: {warning}")


@agents_app.command("plan-apply-codex")
def agents_plan_apply_codex(
    cwd: Path = typer.Option(
        Path("."),
        "--cwd",
        help="Repository root used to resolve .agent-remote.toml.",
    ),
    codex_home: Path | None = typer.Option(
        None,
        "--codex-home",
        help="Codex home used to verify native agent TOML support.",
    ),
    include_disabled: bool = typer.Option(
        False,
        "--include-disabled",
        help="Include disabled agents in the audit plan.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Print JSON output."),
) -> None:
    """Plan Codex-native agent materialization.

    Args:
        cwd [Path]: Repository root used for config resolution.
        codex_home [Path | None]: Optional Codex home override.
        include_disabled [bool]: Whether disabled agents should be included.
        json_output [bool]: Whether to print JSON.
    """
    plan: CodexAgentMaterializationPlan = build_codex_agent_materialization_plan(
        cwd,
        codex_home=codex_home,
        include_disabled=include_disabled,
    )
    if json_output:
        typer.echo(plan.model_dump_json(indent=2))
        return

    typer.echo(f"supported: {plan.supported}")
    for planned_file in plan.files:
        typer.echo(f"{planned_file.agent_id}\t{planned_file.target_path}")
    for warning in plan.warnings:
        typer.echo(f"warning: {warning}")


@agents_app.command("apply-codex")
def agents_apply_codex(
    cwd: Path = typer.Option(
        Path("."),
        "--cwd",
        help="Repository root used to resolve .agent-remote.toml.",
    ),
    codex_home: Path | None = typer.Option(
        None,
        "--codex-home",
        help="Codex home used to verify native agent TOML support.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Plan without writing files."),
    json_output: bool = typer.Option(False, "--json", help="Print JSON output."),
) -> None:
    """Apply Codex-native agent materialization.

    Args:
        cwd [Path]: Repository root used for config resolution.
        codex_home [Path | None]: Optional Codex home override.
        dry_run [bool]: Whether to avoid writing files.
        json_output [bool]: Whether to print JSON.
    """
    plan: CodexAgentMaterializationPlan = build_codex_agent_materialization_plan(
        cwd,
        codex_home=codex_home,
    )
    result: CodexAgentMaterializationApplyResult = apply_codex_agent_materialization(
        plan,
        dry_run=dry_run,
    )
    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        return

    typer.echo(f"dry_run: {result.dry_run}")
    for written_file in result.written_files:
        typer.echo(f"wrote: {written_file}")
    for warning in result.warnings:
        typer.echo(f"warning: {warning}")


@agents_app.command("codex-status")
def agents_codex_status(
    cwd: Path = typer.Option(
        Path("."),
        "--cwd",
        help="Repository root used to resolve .agent-remote.toml.",
    ),
    codex_home: Path | None = typer.Option(
        None,
        "--codex-home",
        help="Codex home used to verify native agent TOML support.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Print JSON output."),
) -> None:
    """Report generated Codex-native agent file status.

    Args:
        cwd [Path]: Repository root used for config resolution.
        codex_home [Path | None]: Optional Codex home override.
        json_output [bool]: Whether to print JSON.
    """
    status: CodexAgentMaterializationStatus = read_codex_agent_materialization_status(
        cwd,
        codex_home=codex_home,
    )
    if json_output:
        typer.echo(status.model_dump_json(indent=2))
        return

    typer.echo(f"up_to_date: {status.up_to_date}")
    for file_status in status.files:
        typer.echo(f"{file_status.agent_id}\t{file_status.matches}\t{file_status.target_path}")
    for warning in status.warnings:
        typer.echo(f"warning: {warning}")
