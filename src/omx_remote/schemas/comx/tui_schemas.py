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
    warnings: tuple[NonEmptyString, ...] = ()
    slash_command_count: int = 0
    mcp_server_count: int = 0
    composed_command_count: int = 0


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
