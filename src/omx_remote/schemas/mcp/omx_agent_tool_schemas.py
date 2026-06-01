from omx_remote.adapter_types.json_types import JsonValue
from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandCatalogListResult,
    CommandExecutionPlan,
    CommandRecipe,
)
from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel
from omx_remote.schemas.run_record_schemas import RunRecord


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


class CompanyRunMcpExecutePayload(StrictSchemaModel):
    """Stable payload returned by the explicit company-run execute MCP tool."""

    ok: bool
    cwd: NonEmptyString
    command_id: NonEmptyString
    qualified_id: NonEmptyString
    dry_run: bool
    status: NonEmptyString
    run_id: NonEmptyString
    run_dir: NonEmptyString
    result_path: NonEmptyString
    company_run_root: NonEmptyString
    blocked_reasons: tuple[str, ...]
    team_launch_attempted: bool
    artifacts: tuple[str, ...]
    warnings: tuple[NonEmptyString, ...]


class CompanyRunMcpStatusPayload(StrictSchemaModel):
    """Stable payload returned by the company-run status MCP tool."""

    ok: bool
    cwd: NonEmptyString
    run_id: NonEmptyString
    status: NonEmptyString
    current_phase: NonEmptyString
    result_path: NonEmptyString
    state_path: NonEmptyString
    company_run_root: NonEmptyString


class CompanyRunMcpArtifactsPayload(StrictSchemaModel):
    """Stable payload returned by the company-run artifacts MCP tool."""

    ok: bool
    cwd: NonEmptyString
    run_id: NonEmptyString
    company_run_root: NonEmptyString
    artifact_paths: tuple[str, ...]
    artifacts: dict[str, JsonValue]
    unsafe_artifact_paths: tuple[str, ...]
