from omx_remote.schemas.comx.tui_schemas import ComxTuiSlashCommand

TUI_SLASH_COMMANDS: tuple[ComxTuiSlashCommand, ...] = (
    ComxTuiSlashCommand(
        name="/help",
        description="Show slash command help.",
        handler_key="help",
        group="core",
    ),
    ComxTuiSlashCommand(
        name="/status",
        description="Show Codex/OMX cockpit status, warnings, and next actions.",
        handler_key="status",
        group="core",
    ),
    ComxTuiSlashCommand(
        name="/surface",
        description="Show native and composed command counts.",
        handler_key="surface",
        group="core",
    ),
    ComxTuiSlashCommand(
        name="/commands",
        description="List composed project command recipes.",
        handler_key="commands",
        group="commands",
    ),
    ComxTuiSlashCommand(
        name="/run",
        description="Preview a composed command recipe. Execution stays outside the TUI.",
        handler_key="run",
        group="commands",
        supports_inline_args=True,
    ),
    ComxTuiSlashCommand(
        name="/route",
        description="Classify a task and show the recommended Codex/OMX route.",
        handler_key="route",
        group="commands",
        supports_inline_args=True,
    ),
    ComxTuiSlashCommand(
        name="/mcp",
        description="List configured MCP servers; use /mcp verbose for diagnostics.",
        handler_key="mcp",
        group="mcp",
        supports_inline_args=True,
    ),
    ComxTuiSlashCommand(
        name="/mcp servers",
        description="Show MCP server registry rows.",
        handler_key="mcp_servers",
        group="mcp",
    ),
    ComxTuiSlashCommand(
        name="/mcp tools",
        description="List tools for one MCP server: /mcp tools <server>.",
        handler_key="mcp_tools",
        group="mcp",
        supports_inline_args=True,
    ),
    ComxTuiSlashCommand(
        name="/mcp call",
        description="Preview an MCP tool call without executing it.",
        handler_key="mcp_call",
        group="mcp",
        supports_inline_args=True,
    ),
    ComxTuiSlashCommand(
        name="/session",
        description="Show current persisted session id and input count.",
        handler_key="session",
        group="sessions",
    ),
    ComxTuiSlashCommand(
        name="/sessions",
        description="List durable comx-agent TUI sessions.",
        handler_key="sessions",
        group="sessions",
    ),
    ComxTuiSlashCommand(
        name="/next",
        description="Show the current recommended next action.",
        handler_key="next",
        group="runtime",
    ),
    ComxTuiSlashCommand(
        name="/team",
        description="Show active OMX Team task/worker state and inspect hints.",
        handler_key="team",
        group="omx",
        supports_inline_args=True,
    ),
    ComxTuiSlashCommand(
        name="/ultragoal",
        description="Show UltraGoal story, ledger, and checkpoint guidance.",
        handler_key="ultragoal",
        group="omx",
        supports_inline_args=True,
    ),
    ComxTuiSlashCommand(
        name="/goal",
        description="Show the active Codex goal bridge state.",
        handler_key="goal",
        group="omx",
        supports_inline_args=True,
    ),
    ComxTuiSlashCommand(
        name="/interview",
        description="Create a clarification-first interview plan artifact.",
        handler_key="interview",
        group="research",
        supports_inline_args=True,
    ),
    ComxTuiSlashCommand(
        name="/research",
        description="Create a staged deep-research workflow plan artifact.",
        handler_key="research",
        group="research",
        supports_inline_args=True,
    ),
    ComxTuiSlashCommand(
        name="/clear",
        description="Clear the terminal and redraw the current frame.",
        handler_key="clear",
        group="local",
    ),
    ComxTuiSlashCommand(
        name="/quit",
        description="Save and exit the TUI loop.",
        aliases=("/exit",),
        handler_key="quit",
        group="local",
    ),
)


def list_tui_slash_commands() -> tuple[ComxTuiSlashCommand, ...]:
    """Return slash commands in presentation order.

    Returns:
        tuple[ComxTuiSlashCommand, ...]: Slash commands.
    """
    return TUI_SLASH_COMMANDS


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


def _command_tokens(command_text: str) -> tuple[str, str]:
    """Split a slash command into command prefix and inline args.

    Args:
        command_text [str]: Normalized command text.

    Returns:
        tuple[str, str]: Prefix and inline args.
    """
    for command in sorted(TUI_SLASH_COMMANDS, key=lambda item: len(item.name), reverse=True):
        names: tuple[str, ...] = (command.name, *command.aliases)
        for candidate in names:
            if command_text == candidate:
                return command.name, ""
            if command.supports_inline_args and command_text.startswith(f"{candidate} "):
                return command.name, command_text[len(candidate) :].strip()
    return command_text, ""


def find_tui_slash_command(command_text: str) -> ComxTuiSlashCommand | None:
    """Find the registered slash command for one input.

    Args:
        command_text [str]: Normalized command text.

    Returns:
        ComxTuiSlashCommand | None: Matching command, if any.
    """
    command_name, _ = _command_tokens(command_text)
    for command in TUI_SLASH_COMMANDS:
        if command.name == command_name:
            return command
    return None


def get_tui_slash_command_args(command_text: str) -> str:
    """Return inline args for a matching command.

    Args:
        command_text [str]: Normalized command text.

    Returns:
        str: Inline args, or an empty string.
    """
    _, args = _command_tokens(command_text)
    return args


def is_known_tui_slash_command(command_text: str) -> bool:
    """Check whether input is a known slash command or alias.

    Args:
        command_text [str]: Normalized input text.

    Returns:
        bool: True when the input matches a registered slash command.
    """
    known: bool = find_tui_slash_command(command_text) is not None
    return known


def format_tui_slash_command_help() -> str:
    """Build the TUI slash-command help text.

    Returns:
        str: Help text.
    """
    lines: list[str] = [
        "slash commands:",
        "type '/' to open completions; use ↑/↓ to select; enter free text as a prompt",
    ]
    current_group = ""
    for command in TUI_SLASH_COMMANDS:
        if command.group != current_group:
            current_group = command.group
            lines.append(f"[{current_group}]")
        usage = command.usage or command.name
        lines.append(f"{usage} - {command.description}")
    help_text: str = "\n".join(lines)
    return help_text
