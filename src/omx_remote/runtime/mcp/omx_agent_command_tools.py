from pathlib import Path

from pydantic import ValidationError

from omx_remote.adapter_types.json_types import JsonObject
from omx_remote.runtime.commands.command_catalog_resolver import (
    CommandCatalogResolutionError,
    load_command_catalog,
    resolve_command_recipe,
)
from omx_remote.runtime.commands.command_recipe_loader import CommandRecipeLoadError
from omx_remote.runtime.commands.command_step_planner import (
    build_command_execution_plan,
)
from omx_remote.runtime.mcp.omx_agent_command_context import recipe_with_context
from omx_remote.runtime.mcp.omx_agent_tool_payloads import (
    catalog_list_result,
    manual_commands,
    next_actions,
    tool_payload,
    usage,
)
from omx_remote.runtime.runs.run_record_writer import write_dry_run_record
from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandCatalog,
    CommandExecutionPlan,
    CommandRecipe,
)
from omx_remote.schemas.mcp.omx_agent_tool_schemas import OmxAgentMcpToolResult
from omx_remote.schemas.runs.run_record_schemas import RunRecord

CUSTOM_WORKFLOW_COMMAND_IDS: tuple[str, ...] = (
    "codex-deep-research",
    "omx-autoresearch-loop",
    "research-interview-prd",
    "company-build-loop",
    "verify-handoff-plus",
    "route-doctor",
    "mcp-onboard-audit",
    "subagent-review-wave",
    "upstream-contract-refresh",
    "skillize-workflow",
    "run-ledger-closeout",
    "alexandria-memory-capture",
    "docs-sync-guardian",
    "dependency-incident-audit",
    "migration-checkpoint-loop",
    "company-discovery-loop",
    "company-build-loop-plus",
    "product-council",
    "team-sprint-plan",
    "subagent-research-swarm",
    "ultragoal-story-factory",
    "qa-war-room",
    "librarian-closeout",
)


class OmxAgentMcpCommandError(ValueError):
    """Raised when an omx-agent MCP command tool cannot build a safe plan."""


def _resolved_cwd(cwd: str | Path) -> Path:
    """Resolve a caller-provided working directory.

    Args:
        cwd [str | Path]: Working directory supplied by CLI or MCP server config.

    Returns:
        Path: Absolute working directory.
    """
    resolved = Path(cwd).expanduser().resolve()
    return resolved


def _resolved_config_path(config_path: str | Path | None) -> Path | None:
    """Resolve an optional command config path.

    Args:
        config_path [str | Path | None]: Optional config path.

    Returns:
        Path | None: Resolved config path when supplied.
    """
    if config_path is None:
        missing_config: None = None
        return missing_config
    resolved = Path(config_path).expanduser().resolve()
    return resolved


def _load_catalog(cwd: Path, config_path: Path | None) -> CommandCatalog:
    """Load the command catalog for MCP tools.

    Args:
        cwd [Path]: Repository root.
        config_path [Path | None]: Optional config path.

    Returns:
        CommandCatalog: Loaded catalog.
    """
    catalog = load_command_catalog(cwd=cwd, config_path=config_path)
    return catalog


def _load_recipe(cwd: Path, config_path: Path | None, command_id: str) -> CommandRecipe:
    """Resolve a command recipe by short or qualified id.

    Args:
        cwd [Path]: Repository root.
        config_path [Path | None]: Optional config path.
        command_id [str]: Command id.

    Returns:
        CommandRecipe: Resolved recipe.
    """
    catalog = _load_catalog(cwd, config_path)
    recipe = resolve_command_recipe(catalog, command_id)
    return recipe


def list_command_tools_payload(
    cwd: str | Path,
    config_path: str | Path | None = None,
) -> JsonObject:
    """Return the command catalog through the omx-agent MCP contract.

    Args:
        cwd [str | Path]: Repository root.
        config_path [str | Path | None]: Optional command config path.

    Returns:
        JsonObject: MCP JSON payload.
    """
    root = _resolved_cwd(cwd)
    config = _resolved_config_path(config_path)
    catalog = _load_catalog(root, config)
    result = OmxAgentMcpToolResult(
        cwd=str(root),
        catalog=catalog_list_result(catalog),
        usage=usage(root),
        next_actions=(
            "Call omx_agent_preview_command with a command_id to inspect a safe dry-run plan.",
            "Use dedicated tools for flagship workflows or omx_agent_preview_command for any custom recipe.",
        ),
    )
    payload = tool_payload(result)
    return payload


def show_command_tool_payload(
    cwd: str | Path,
    command_id: str,
    config_path: str | Path | None = None,
) -> JsonObject:
    """Return one command recipe through the omx-agent MCP contract.

    Args:
        cwd [str | Path]: Repository root.
        command_id [str]: Command id.
        config_path [str | Path | None]: Optional command config path.

    Returns:
        JsonObject: MCP JSON payload.
    """
    root = _resolved_cwd(cwd)
    config = _resolved_config_path(config_path)
    recipe = _load_recipe(root, config, command_id)
    result = OmxAgentMcpToolResult(
        cwd=str(root),
        command_id=recipe.id,
        qualified_id=recipe.qualified_id,
        recipe=recipe,
        usage=usage(root),
        next_actions=(
            f"Preview this recipe with omx_agent_preview_command command_id={recipe.qualified_id}.",
        ),
    )
    payload = tool_payload(result)
    return payload


def preview_command_tool_payload(
    cwd: str | Path,
    command_id: str,
    config_path: str | Path | None = None,
    objective: str | None = None,
    topic: str | None = None,
    rubric: str | None = None,
    slug: str | None = None,
    prd_path: str | None = None,
    notes: str | None = None,
    record_run: bool = False,
) -> JsonObject:
    """Build a dry-run plan for one command recipe.

    Args:
        cwd [str | Path]: Repository root.
        command_id [str]: Command id.
        config_path [str | Path | None]: Optional command config path.
        objective [str | None]: User objective.
        topic [str | None]: Research topic.
        rubric [str | None]: Research rubric.
        slug [str | None]: Durable run slug.
        prd_path [str | None]: PRD or brief path.
        notes [str | None]: Additional notes.
        record_run [bool]: Whether to write a dry-run record.

    Returns:
        JsonObject: MCP JSON payload.
    """
    root = _resolved_cwd(cwd)
    config = _resolved_config_path(config_path)
    recipe = _load_recipe(root, config, command_id)
    contextual_recipe = recipe_with_context(
        recipe,
        objective=objective,
        topic=topic,
        rubric=rubric,
        slug=slug,
        prd_path=prd_path,
        notes=notes,
    )
    plan: CommandExecutionPlan = build_command_execution_plan(
        contextual_recipe,
        cwd=root,
        dry_run=True,
    )
    run_record: RunRecord | None = None
    if record_run:
        run_record = write_dry_run_record(plan, cwd=root)
    result = OmxAgentMcpToolResult(
        cwd=str(root),
        command_id=recipe.id,
        qualified_id=recipe.qualified_id,
        plan=plan,
        run_record=run_record,
        usage=usage(root),
        manual_commands=manual_commands(plan),
        next_actions=next_actions(plan, run_record),
        warnings=(
            "MCP tool returns a dry-run plan only; it does not execute native Codex/OMX commands.",
        ),
    )
    payload = tool_payload(result)
    return payload


def safe_tool_error_payload(error: Exception, cwd: str | Path) -> JsonObject:
    """Normalize known command errors into an MCP JSON payload.

    Args:
        error [Exception]: Error raised by a tool handler.
        cwd [str | Path]: Working directory associated with the call.

    Returns:
        JsonObject: Error payload.
    """
    root = _resolved_cwd(cwd)
    known_error_types = (
        CommandCatalogResolutionError,
        CommandRecipeLoadError,
        ValidationError,
        ValueError,
    )
    if not isinstance(error, known_error_types):
        raise error
    error_result = OmxAgentMcpToolResult(cwd=str(root), ok=False, usage=usage(root))
    payload: JsonObject = tool_payload(error_result)
    payload["error"] = str(error)
    return payload
