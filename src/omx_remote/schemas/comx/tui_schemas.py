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


class ComxTuiSlashCommand(StrictSchemaModel):
    """Represents one interactive TUI slash command."""

    name: NonEmptyString
    description: NonEmptyString
    aliases: tuple[NonEmptyString, ...] = ()
