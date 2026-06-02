from omx_remote.schemas.commands.command_runtime_option_schemas import (
    CommandRuntimeOptions,
)
from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel


class ComxTuiStatusLine(StrictSchemaModel):
    """Represents the compact statusline rendered by the TUI."""

    model_label: NonEmptyString
    workspace: NonEmptyString
    permission_label: NonEmptyString
    runtime_label: NonEmptyString
    goal_label: NonEmptyString
    ralph_label: NonEmptyString
    teams_label: NonEmptyString


class ComxTuiSnapshot(StrictSchemaModel):
    """Represents the read-only data needed to render one TUI frame."""

    title: NonEmptyString
    subtitle: NonEmptyString
    status_line: ComxTuiStatusLine
    prompt: NonEmptyString
    tips: tuple[NonEmptyString, ...]
    command_palette: tuple[NonEmptyString, ...]
    operation_hints: tuple[NonEmptyString, ...]
    warnings: tuple[NonEmptyString, ...] = ()
    slash_command_count: int = 0
    mcp_server_count: int = 0
    composed_command_count: int = 0


class ComxTuiRuntimeEvidenceSummary(StrictSchemaModel):
    """Represents runtime evidence surfaced by TUI status panels."""

    latest_run_id: NonEmptyString | None
    artifact_count: int
    artifact_references: tuple[NonEmptyString, ...]
    memory_recall_path: NonEmptyString | None
    team_dispatch_path: NonEmptyString | None
    team_worker_count: int
    command_recipe_count: int
    warnings: tuple[NonEmptyString, ...]


class ComxTuiSlashCommand(StrictSchemaModel):
    """Represents one interactive TUI slash command."""

    name: NonEmptyString
    description: NonEmptyString
    aliases: tuple[NonEmptyString, ...] = ()
    handler_key: NonEmptyString = "unhandled"
    group: NonEmptyString = "general"
    supports_inline_args: bool = False
    available_during_task: bool = True
    mutates_runtime: bool = False
    usage: NonEmptyString | None = None


class ComxTuiCommandResult(StrictSchemaModel):
    """Represents a rendered result from a TUI slash command."""

    command: NonEmptyString
    title: NonEmptyString
    body: NonEmptyString
    read_only: bool = True
    artifact_path: NonEmptyString | None = None
    warnings: tuple[NonEmptyString, ...] = ()


class ComxTuiRunPreviewArgs(StrictSchemaModel):
    """Parsed `/run` preview arguments."""

    recipe_id: NonEmptyString
    task_text: NonEmptyString | None = None
    runtime_options: CommandRuntimeOptions | None = None
