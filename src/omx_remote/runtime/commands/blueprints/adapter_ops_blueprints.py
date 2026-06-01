from omx_remote.runtime.commands.blueprints.recipe_blueprint_factories import (
    prompt_step,
    role_lane,
)
from omx_remote.runtime.prompt_assets import prompt_asset_path
from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandRecipe,
    CommandStep,
    CommandStepCommand,
)
from omx_remote.schemas.commands.command_role_schemas import CommandRoleExecution
from omx_remote.shared.omx_enums.command_enums import (
    CommandAdapterOpsId,
    CommandNamespace,
    CommandRecipeCategory,
    CommandRisk,
    CommandSource,
)

ADAPTER_OPS_LOCAL_IDS: tuple[CommandAdapterOpsId, ...] = (
    CommandAdapterOpsId.MCP_AUDIT,
    CommandAdapterOpsId.CONTRACT_REFRESH,
    CommandAdapterOpsId.SKILLIZE,
    CommandAdapterOpsId.RUN_LEDGER,
    CommandAdapterOpsId.MEMORY_CAPTURE,
)

ADAPTER_OPS_DISPLAY_IDS: tuple[str, ...] = tuple(
    f"{CommandNamespace.ADAPTER_OPS} {command_id.value}"
    for command_id in ADAPTER_OPS_LOCAL_IDS
)

ADAPTER_OPS_COMMAND_IDS: tuple[str, ...] = ADAPTER_OPS_DISPLAY_IDS


def _ops_recipe(
    local_id: CommandAdapterOpsId,
    description: str,
    risk: CommandRisk,
    prompt_file: str,
    output_path: str,
) -> CommandRecipe:
    """Build one adapter-ops maintenance recipe.

    Args:
        local_id [CommandAdapterOpsId]: Namespace-local maintenance command id.
        description [str]: Command description.
        risk [CommandRisk]: Command risk.
        prompt_file [str]: Prompt asset path.
        output_path [str]: Expected maintenance handoff path.

    Returns:
        CommandRecipe: Adapter-ops command recipe.
    """
    step = prompt_step(
        "Prepare adapter-ops maintenance handoff for: <task>.",
        prompt_file=prompt_file,
        expected_artifacts=(output_path,),
        role_lanes=(
            role_lane(
                lane_id=f"adapter_ops_{local_id.value.replace('-', '_')}",
                execution=CommandRoleExecution.LOCAL_EVIDENCE,
                purpose="Prepare typed maintenance evidence and handoff without mixing into public workflows.",
                artifact=output_path,
            ),
        ),
    )
    recipe = CommandRecipe(
        id=local_id.value,
        source=CommandSource.BUILTIN,
        description=description,
        namespace=CommandNamespace.ADAPTER_OPS,
        category=CommandRecipeCategory.MAINTENANCE,
        risk=risk,
        steps=(step,),
    )
    return recipe


def _memory_capture_recipe() -> CommandRecipe:
    """Build the adapter-ops memory-capture recipe.

    Returns:
        CommandRecipe: Memory-capture recipe.
    """
    output_path = ".comx-agent/runs/adapter-ops/memory-capture/handoff.md"
    recipe = CommandRecipe(
        id=CommandAdapterOpsId.MEMORY_CAPTURE.value,
        source=CommandSource.BUILTIN,
        description="Capture curated project memory through Alexandria MCP tool handoff.",
        namespace=CommandNamespace.ADAPTER_OPS,
        category=CommandRecipeCategory.MAINTENANCE,
        risk=CommandRisk.WRITES_FILES,
        steps=(
            CommandStep(
                command=CommandStepCommand.MCP_TOOL,
                prompt_file=prompt_asset_path(
                    "adapter-ops",
                    "memory-capture",
                    "memory-capture.md",
                ),
                inline_prompt=(
                    "Use Alexandria MCP tools for curated memory capture. Store verified "
                    "decisions, artifact paths, rejected alternatives, and skill candidates."
                ),
                mcp_server="alexandria",
                mcp_tool="alexandria_save_note",
                mcp_arguments={
                    "project": "omx-agent-adapter",
                    "alexandria_type": "context",
                    "title": "<descriptive-title>",
                    "body": "<curated-summary>",
                },
                expected_artifacts=(output_path,),
                role_lanes=(
                    role_lane(
                        lane_id="adapter_ops_memory_capture",
                        execution=CommandRoleExecution.ALEXANDRIA_MEMORY,
                        purpose="Use Alexandria MCP tools for curated memory capture and reindex guidance.",
                        artifact=output_path,
                    ),
                ),
            ),
        ),
    )
    return recipe


def build_adapter_ops_blueprints() -> tuple[CommandRecipe, ...]:
    """Build adapter-ops maintenance recipes.

    Returns:
        tuple[CommandRecipe, ...]: Adapter maintenance recipes.
    """
    recipes = (
        _ops_recipe(
            local_id=CommandAdapterOpsId.MCP_AUDIT,
            description="Audit MCP configuration, tool visibility, OAuth/env risks, and safe registration guidance.",
            risk=CommandRisk.READ_ONLY,
            prompt_file=prompt_asset_path("adapter-ops", "mcp-audit", "mcp-audit.md"),
            output_path=".comx-agent/runs/adapter-ops/mcp-audit/report.md",
        ),
        _ops_recipe(
            local_id=CommandAdapterOpsId.CONTRACT_REFRESH,
            description="Plan probe suites and fixture comparisons for upstream Codex/OMX contract drift.",
            risk=CommandRisk.READ_ONLY,
            prompt_file=prompt_asset_path(
                "adapter-ops",
                "contract-refresh",
                "contract-refresh.md",
            ),
            output_path=".comx-agent/runs/adapter-ops/contract-refresh/report.md",
        ),
        _ops_recipe(
            local_id=CommandAdapterOpsId.SKILLIZE,
            description="Convert a validated recipe or run record into a Codex skill plan and validation handoff.",
            risk=CommandRisk.WRITES_FILES,
            prompt_file=prompt_asset_path("adapter-ops", "skillize", "skillize.md"),
            output_path=".comx-agent/runs/adapter-ops/skillize/handoff.md",
        ),
        _ops_recipe(
            local_id=CommandAdapterOpsId.RUN_LEDGER,
            description="Inspect run records, missing artifacts, replay evidence, and stale run notes.",
            risk=CommandRisk.READ_ONLY,
            prompt_file=prompt_asset_path("adapter-ops", "run-ledger", "run-ledger.md"),
            output_path=".comx-agent/runs/adapter-ops/run-ledger/report.md",
        ),
        _memory_capture_recipe(),
    )
    return recipes
