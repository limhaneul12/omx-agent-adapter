from omx_remote.schemas.comx.tui_schemas import ComxTuiSlashCommand

TUI_SLASH_COMMANDS: tuple[ComxTuiSlashCommand, ...] = (
    ComxTuiSlashCommand(
        name="/help",
        description="Show slash command help.",
    ),
    ComxTuiSlashCommand(
        name="/surface",
        description="Show native/composed command counts.",
    ),
    ComxTuiSlashCommand(
        name="/mcp servers",
        description="Show MCP server counts.",
    ),
    ComxTuiSlashCommand(
        name="/session",
        description="Show current persisted session id and input count.",
    ),
    ComxTuiSlashCommand(
        name="/next",
        description="Show the current recommended next action.",
    ),
    ComxTuiSlashCommand(
        name="/clear",
        description="Clear the terminal and redraw the current frame.",
    ),
    ComxTuiSlashCommand(
        name="/quit",
        description="Save and exit the TUI loop.",
        aliases=("/exit",),
    ),
)


def format_tui_slash_command_help() -> str:
    """Build the TUI slash-command help text.

    Returns:
        str: Help text.
    """
    lines: list[str] = [
        "slash commands:",
        "type '/' to open completions; use ↑/↓ to select; enter free text as a prompt",
    ]
    lines.extend(
        f"{command.name} - {command.description}" for command in TUI_SLASH_COMMANDS
    )
    help_text: str = "\n".join(lines)
    return help_text


def list_tui_slash_completion_items() -> tuple[tuple[str, str], ...]:
    """List slash command completion display items.

    Returns:
        tuple[tuple[str, str], ...]: Command name and description pairs.
    """
    completion_items: tuple[tuple[str, str], ...] = tuple(
        (command.name, command.description) for command in TUI_SLASH_COMMANDS
    )
    return completion_items


def normalize_tui_command_text(command_text: str) -> str:
    """Normalize TUI input text.

    Args:
        command_text [str]: Raw input text.

    Returns:
        str: Trimmed command text.
    """
    normalized_text: str = command_text.strip()
    return normalized_text


def is_known_tui_slash_command(command_text: str) -> bool:
    """Check whether input is a known slash command or alias.

    Args:
        command_text [str]: Normalized input text.

    Returns:
        bool: True when the input matches a registered slash command.
    """
    known_names: set[str] = set()
    for command in TUI_SLASH_COMMANDS:
        known_names.add(command.name)
        known_names.update(command.aliases)

    known: bool = command_text in known_names
    return known
