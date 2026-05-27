from pathlib import Path
from typing import cast

from omx_remote.adapter_types.json_types import JsonObject
from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandCatalog,
    CommandCatalogEntry,
    CommandCatalogListResult,
    CommandExecutionPlan,
    CommandSource,
)
from omx_remote.schemas.mcp.omx_agent_tool_schemas import (
    OmxAgentMcpToolResult,
    OmxAgentMcpUsage,
)
from omx_remote.schemas.runs.run_record_schemas import RunRecord


def usage(cwd: Path) -> OmxAgentMcpUsage:
    """Build common usage hints for omx-agent MCP tool responses.

    Args:
        cwd [Path]: Repository root.

    Returns:
        OmxAgentMcpUsage: Reusable usage hints.
    """
    cwd_text = str(cwd)
    tool_usage = OmxAgentMcpUsage(
        register_server=(
            "comx-agent mcp add omx_agent --cwd . -- "
            f"comx-agent mcp serve --cwd {cwd_text}"
        ),
        list_tools="comx-agent mcp tools omx_agent --cwd . --execute --json",
        preview_command=(
            "comx-agent mcp call omx_agent omx_agent_preview_command "
            '--arguments-json \'{"command_id":"builtin:verify-handoff-plus"}\' '
            "--execute --json"
        ),
        tui_preview="/run builtin:verify-handoff-plus",
    )
    return tool_usage


def catalog_list_result(catalog: CommandCatalog) -> CommandCatalogListResult:
    """Build typed command catalog list output.

    Args:
        catalog [CommandCatalog]: Loaded command catalog.

    Returns:
        CommandCatalogListResult: List result contract.
    """
    entries: tuple[CommandCatalogEntry, ...] = tuple(
        CommandCatalogEntry(
            id=recipe.id,
            qualified_id=recipe.qualified_id,
            source=recipe.source,
            description=recipe.description,
            risk=recipe.risk,
            step_count=len(recipe.steps),
        )
        for recipe in catalog.commands
    )
    builtin_count = sum(
        1 for recipe in catalog.commands if recipe.source == CommandSource.BUILTIN
    )
    repo_count = sum(
        1 for recipe in catalog.commands if recipe.source == CommandSource.REPO
    )
    result = CommandCatalogListResult(
        commands=entries,
        builtin_count=builtin_count,
        repo_count=repo_count,
    )
    return result


def tool_payload(result: OmxAgentMcpToolResult) -> JsonObject:
    """Convert a typed tool result to a JSON-compatible dictionary.

    This is the MCP transport boundary: FastMCP expects a plain JSON-like object,
    while the adapter core keeps a Pydantic contract.

    Args:
        result [OmxAgentMcpToolResult]: Typed tool result.

    Returns:
        JsonObject: JSON-compatible payload.
    """
    payload = cast(JsonObject, result.model_dump(mode="json"))
    return payload


def manual_commands(plan: CommandExecutionPlan) -> tuple[str, ...]:
    """Render native argv lines from one dry-run plan.

    Args:
        plan [CommandExecutionPlan]: Command plan.

    Returns:
        tuple[str, ...]: Shell-readable command previews.
    """
    commands = tuple(" ".join(step.native_argv) for step in plan.steps)
    return commands


def next_actions(
    plan: CommandExecutionPlan, run_record: RunRecord | None
) -> tuple[str, ...]:
    """Build next-action hints for an MCP command plan.

    Args:
        plan [CommandExecutionPlan]: Command plan.
        run_record [RunRecord | None]: Optional dry-run record.

    Returns:
        tuple[str, ...]: Next-action hints.
    """
    actions: list[str] = [
        "Review blocked_reasons before executing any native command.",
        f"TUI preview: /run {plan.qualified_id}",
        "Execute high-risk commands only after an explicit user confirmation.",
    ]
    if run_record is not None:
        actions.append(f"Dry-run record written: {run_record.run_id}")
    if plan.blocked_reasons:
        actions.append("Resolve blockers before handoff or execution.")
    built_actions: tuple[str, ...] = tuple(actions)
    return built_actions
