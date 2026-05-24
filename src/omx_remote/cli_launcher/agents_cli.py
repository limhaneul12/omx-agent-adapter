from pathlib import Path

import orjson
import typer
from pydantic import ValidationError

from omx_remote.runtime.agents.agent_config_loader import (
    AgentConfigLoadError,
    load_agent_config,
)
from omx_remote.schemas.agents.agent_config_schemas import (
    AgentConfig,
    AgentConfigSet,
    AgentListResult,
    AgentShowResult,
    AgentValidationResult,
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
