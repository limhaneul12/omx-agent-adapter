from pathlib import Path

from omx_remote.runtime.commands.catalog.command_catalog_projection import (
    catalog_list_result,
)
from omx_remote.runtime.commands.catalog.command_catalog_resolver import (
    load_command_catalog,
)
from omx_remote.schemas.commands.command_recipe_schemas import CommandCatalog
from omx_remote.schemas.comx.control_surface_schemas import (
    ComxControlSurfaceInventory,
    ComxNativeCommand,
)


def build_native_command_inventory() -> tuple[ComxNativeCommand, ...]:
    """Build the direct command inventory exposed by comx-agent.

    Returns:
        tuple[ComxNativeCommand, ...]: Native command surfaces.
    """
    commands: tuple[ComxNativeCommand, ...] = (
        ComxNativeCommand(
            name="tui",
            description="Open the Codex-like terminal console with slash completions.",
            read_only_default=True,
            mutates_runtime=False,
        ),
        ComxNativeCommand(
            name="sessions",
            description="Inspect durable comx-agent TUI session records.",
            read_only_default=True,
            mutates_runtime=False,
        ),
        ComxNativeCommand(
            name="daemon",
            description="Start, attach, inspect, and stop tmux-backed TUI background sessions.",
            read_only_default=False,
            mutates_runtime=True,
        ),
        ComxNativeCommand(
            name="surface",
            description="Explain native command support versus composed recipes.",
            read_only_default=True,
            mutates_runtime=False,
        ),
        ComxNativeCommand(
            name="mcp",
            description="Consume external MCP servers and tools as a client.",
            read_only_default=True,
            mutates_runtime=False,
        ),
        ComxNativeCommand(
            name="cockpit",
            description="Read repo-scoped operating-lane evidence.",
            read_only_default=True,
            mutates_runtime=False,
        ),
        ComxNativeCommand(
            name="next",
            description="Recommend the next safe read-only action.",
            read_only_default=True,
            mutates_runtime=False,
        ),
        ComxNativeCommand(
            name="route",
            description="Classify tasks and recommend Codex/OMX routes.",
            read_only_default=True,
            mutates_runtime=False,
        ),
        ComxNativeCommand(
            name="commands",
            description="Inspect composed command recipes.",
            read_only_default=True,
            mutates_runtime=False,
        ),
        ComxNativeCommand(
            name="run",
            description="Dry-run composed command recipes.",
            read_only_default=True,
            mutates_runtime=False,
        ),
        ComxNativeCommand(
            name="preflight",
            description="Run safety checks for routes and command recipes.",
            read_only_default=True,
            mutates_runtime=False,
        ),
        ComxNativeCommand(
            name="ultragoal",
            description="Read native OMX UltraGoal capability/status.",
            read_only_default=True,
            mutates_runtime=False,
        ),
        ComxNativeCommand(
            name="team",
            description="Read and operate typed OMX Team surfaces.",
            read_only_default=False,
            mutates_runtime=True,
        ),
        ComxNativeCommand(
            name="ralph",
            description="Guarded Ralph launch/resume/cleanup control.",
            read_only_default=False,
            mutates_runtime=True,
        ),
        ComxNativeCommand(
            name="ultrawork",
            description="Guarded Ultrawork launch/resume/cleanup control.",
            read_only_default=False,
            mutates_runtime=True,
        ),
        ComxNativeCommand(
            name="goal",
            description="Adapter-tracked native Codex Goal lifecycle surfaces.",
            read_only_default=False,
            mutates_runtime=True,
        ),
        ComxNativeCommand(
            name="agents",
            description="Validate and materialize repo-local subagent config.",
            read_only_default=True,
            mutates_runtime=False,
        ),
        ComxNativeCommand(
            name="probes",
            description="Probe upstream Codex/OMX command contracts.",
            read_only_default=True,
            mutates_runtime=False,
        ),
        ComxNativeCommand(
            name="runtime",
            description="Read active OMX runtime modes and status.",
            read_only_default=True,
            mutates_runtime=False,
        ),
        ComxNativeCommand(
            name="history",
            description="Search local session/history artifacts.",
            read_only_default=True,
            mutates_runtime=False,
        ),
        ComxNativeCommand(
            name="adapt",
            description="Inspect OMX adapter foundation envelopes.",
            read_only_default=True,
            mutates_runtime=False,
        ),
        ComxNativeCommand(
            name="runs",
            description="Inspect recorded dry-run plans and handoffs.",
            read_only_default=True,
            mutates_runtime=False,
        ),
        ComxNativeCommand(
            name="prd",
            description="Validate typed PRD artifacts.",
            read_only_default=True,
            mutates_runtime=False,
        ),
    )
    return commands


def build_comx_control_surface_inventory(
    cwd: str | Path | None = None,
    config_path: str | Path | None = None,
) -> ComxControlSurfaceInventory:
    """Build the complete comx-agent native/composed surface inventory.

    Args:
        cwd [str | Path | None]: Repository root for recipe config.
        config_path [str | Path | None]: Optional config override.

    Returns:
        ComxControlSurfaceInventory: Typed command surface inventory.
    """
    catalog: CommandCatalog = load_command_catalog(cwd=cwd, config_path=config_path)
    composed_commands = catalog_list_result(catalog).commands
    native_commands: tuple[ComxNativeCommand, ...] = build_native_command_inventory()
    inventory = ComxControlSurfaceInventory(
        product_name="comx-agent",
        native_commands=native_commands,
        composed_commands=composed_commands,
        native_count=len(native_commands),
        composed_count=len(composed_commands),
        summary=(
            "native_commands are direct comx-agent control surfaces; "
            "composed_commands are typed recipes assembled from Codex/OMX/local/MCP steps."
        ),
    )
    return inventory
