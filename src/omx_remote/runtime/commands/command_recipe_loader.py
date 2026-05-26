import tomllib
from pathlib import Path
from typing import Final

from omx_remote.runtime.agents.agent_config_loader import DEFAULT_AGENT_CONFIG_FILENAME
from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandRecipe,
    CommandSource,
    CommandStep,
    CommandStepCommand,
    RepoCommandDefinition,
)

COMMANDS_TOP_LEVEL_SECTION: Final[str] = "commands"
RESERVED_TOP_LEVEL_SECTIONS: Final[frozenset[str]] = frozenset(
    {"agents", COMMANDS_TOP_LEVEL_SECTION, "routes", "mcp", "mcp_servers"}
)


class CommandRecipeLoadError(ValueError):
    """Raised when repo command recipe TOML cannot be loaded."""


def _resolve_config_path(cwd: str | Path | None, config_path: str | Path | None) -> Path:
    """Resolve the repo command config path.

    Args:
        cwd [str | Path | None]: Base working directory for relative paths.
        config_path [str | Path | None]: Optional config path override.

    Returns:
        Path: Config path to read.
    """
    root_path: Path = Path.cwd() if cwd is None else Path(cwd)
    if config_path is None:
        resolved_path: Path = root_path / DEFAULT_AGENT_CONFIG_FILENAME
        return resolved_path

    candidate_path = Path(config_path)
    if candidate_path.is_absolute():
        resolved_path = candidate_path
        return resolved_path

    resolved_path = root_path / candidate_path
    return resolved_path


def _load_toml_object(config_path: Path) -> dict[str, object]:
    """Load one TOML root object.

    Args:
        config_path [Path]: TOML path to read.

    Returns:
        dict[str, object]: Parsed TOML root object.
    """
    try:
        config_text: str = config_path.read_text()
        parsed_toml: dict[str, object] = tomllib.loads(config_text)
    except tomllib.TOMLDecodeError as error:
        raise CommandRecipeLoadError(
            f"Command config at {config_path} contains malformed TOML: {error}"
        ) from error
    except OSError as error:
        raise CommandRecipeLoadError(
            f"Command config at {config_path} could not be read: {error}"
        ) from error

    return parsed_toml


def _validate_top_level_sections(parsed_toml: dict[str, object], config_path: Path) -> None:
    """Validate supported top-level TOML sections.

    Args:
        parsed_toml [dict[str, object]]: Parsed TOML root object.
        config_path [Path]: Source path for error messages.
    """
    unknown_sections: set[str] = set(parsed_toml) - RESERVED_TOP_LEVEL_SECTIONS
    if unknown_sections:
        unknown_text: str = ", ".join(sorted(unknown_sections))
        raise CommandRecipeLoadError(
            f"Command config at {config_path} contains unsupported top-level section(s): {unknown_text}"
        )


def _command_from_provider_mode(provider: str | None, mode: str | None) -> CommandStepCommand:
    """Map simple recipe provider/mode fields to a step command.

    Args:
        provider [str | None]: Recipe provider value.
        mode [str | None]: Recipe mode value.

    Returns:
        CommandStepCommand: Step command enum.
    """
    if provider == "codex" and mode == "exec":
        command: CommandStepCommand = CommandStepCommand.CODEX_EXEC
        return command
    if provider == "omx" and mode == "exec":
        command = CommandStepCommand.OMX_EXEC
        return command
    if provider == "omx" and mode == "ultragoal":
        command = CommandStepCommand.OMX_ULTRAGOAL
        return command
    if provider == "omx" and mode == "team":
        command = CommandStepCommand.OMX_TEAM
        return command
    if provider == "omx" and mode == "ralph":
        command = CommandStepCommand.OMX_RALPH
        return command
    if provider == "local" or mode == "local":
        command = CommandStepCommand.LOCAL
        return command
    if provider == "mcp" or mode == "mcp_tool":
        command = CommandStepCommand.MCP_TOOL
        return command
    if mode == "prompt":
        command = CommandStepCommand.PROMPT_ONLY
        return command

    raise CommandRecipeLoadError(
        f"Unsupported command recipe provider/mode combination: provider={provider!r}, mode={mode!r}"
    )


def _definition_to_recipe(command_id: str, definition: RepoCommandDefinition) -> CommandRecipe:
    """Convert one repo command definition into a stable recipe.

    Args:
        command_id [str]: Command id from TOML table name.
        definition [RepoCommandDefinition]: Validated repo command definition.

    Returns:
        CommandRecipe: Stable command recipe.
    """
    if definition.steps is not None:
        steps: tuple[CommandStep, ...] = definition.steps
    else:
        command: CommandStepCommand = _command_from_provider_mode(
            definition.provider,
            definition.mode,
        )
        steps = (
            CommandStep(
                command=command,
                agent=definition.agent,
                argv=definition.argv,
                prompt_file=definition.prompt_file,
                inline_prompt=definition.inline_prompt,
                brief_file=definition.brief_file,
                mcp_server=definition.mcp_server,
                mcp_tool=definition.mcp_tool,
                mcp_arguments=definition.mcp_arguments,
                output_last_message=definition.output_last_message,
                expected_artifacts=definition.expected_artifacts,
            ),
        )

    recipe = CommandRecipe(
        id=command_id,
        source=CommandSource.REPO,
        description=definition.description,
        risk=definition.risk,
        steps=steps,
    )
    return recipe


def _load_repo_command_payloads(
    parsed_toml: dict[str, object],
    config_path: Path,
) -> tuple[CommandRecipe, ...]:
    """Load repo-defined command recipe payloads from parsed TOML.

    Args:
        parsed_toml [dict[str, object]]: Parsed TOML root object.
        config_path [Path]: Source path for error messages.

    Returns:
        tuple[CommandRecipe, ...]: Loaded repo command recipes.
    """
    raw_commands_section: object = parsed_toml.get(COMMANDS_TOP_LEVEL_SECTION, {})
    if not isinstance(raw_commands_section, dict):
        raise CommandRecipeLoadError(
            f"Command config at {config_path} must define [commands] as a TOML table."
        )

    recipes: list[CommandRecipe] = []
    for command_id, raw_command_payload in raw_commands_section.items():
        if not isinstance(command_id, str):
            raise CommandRecipeLoadError(
                f"Command config at {config_path} contains a non-string command id."
            )
        if not isinstance(raw_command_payload, dict):
            raise CommandRecipeLoadError(
                f"Command config at {config_path} must define [commands.{command_id}] as a TOML table."
            )
        definition = RepoCommandDefinition.model_validate(raw_command_payload)
        recipe: CommandRecipe = _definition_to_recipe(command_id, definition)
        recipes.append(recipe)

    loaded_recipes: tuple[CommandRecipe, ...] = tuple(recipes)
    return loaded_recipes


def load_repo_command_recipes(
    cwd: str | Path | None = None,
    config_path: str | Path | None = None,
) -> tuple[CommandRecipe, ...]:
    """Load repo-defined command recipes from `.agent-remote.toml`.

    Args:
        cwd [str | Path | None]: Base working directory for default/relative config paths.
        config_path [str | Path | None]: Optional config path override.

    Returns:
        tuple[CommandRecipe, ...]: Repo-defined command recipes.
    """
    resolved_config_path: Path = _resolve_config_path(cwd, config_path)
    if not resolved_config_path.exists():
        empty_recipes: tuple[CommandRecipe, ...] = ()
        return empty_recipes

    parsed_toml: dict[str, object] = _load_toml_object(resolved_config_path)
    _validate_top_level_sections(parsed_toml, resolved_config_path)
    loaded_recipes: tuple[CommandRecipe, ...] = _load_repo_command_payloads(
        parsed_toml,
        resolved_config_path,
    )
    return loaded_recipes
