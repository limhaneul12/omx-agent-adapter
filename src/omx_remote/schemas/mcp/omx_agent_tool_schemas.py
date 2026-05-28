from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandCatalogListResult,
    CommandExecutionPlan,
    CommandRecipe,
)
from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel
from omx_remote.schemas.runs.run_record_schemas import RunRecord


class OmxAgentMcpUsage(StrictSchemaModel):
    """Human-facing usage hints returned by the omx-agent MCP server."""

    register_server: NonEmptyString
    list_tools: NonEmptyString
    preview_command: NonEmptyString
    tui_preview: NonEmptyString


class OmxAgentMcpToolResult(StrictSchemaModel):
    """Stable JSON payload returned by omx-agent MCP tools."""

    ok: bool = True
    cwd: NonEmptyString
    command_id: NonEmptyString | None = None
    qualified_id: NonEmptyString | None = None
    catalog: CommandCatalogListResult | None = None
    recipe: CommandRecipe | None = None
    plan: CommandExecutionPlan | None = None
    run_record: RunRecord | None = None
    usage: OmxAgentMcpUsage
    manual_commands: tuple[NonEmptyString, ...] = ()
    next_actions: tuple[NonEmptyString, ...] = ()
    warnings: tuple[NonEmptyString, ...] = ()
