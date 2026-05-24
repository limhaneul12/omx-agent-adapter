from enum import StrEnum

from pydantic import Field, model_validator

from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel


class CommandSource(StrEnum):
    """Sources that can provide project-owned command recipes."""

    BUILTIN = "builtin"
    REPO = "repo"
    ONE_OFF = "one_off"


class CommandRisk(StrEnum):
    """Command risk classes used for dry-run planning."""

    READ_ONLY = "read_only"
    WRITES_FILES = "writes_files"
    LAUNCHES_RUNTIME = "launches_runtime"
    LONG_RUNNING = "long_running"
    EXTERNAL_NETWORK = "external_network"


class CommandStepCommand(StrEnum):
    """Supported composed-command step kinds."""

    CODEX_EXEC = "codex_exec"
    OMX_EXEC = "omx_exec"
    OMX_ULTRAGOAL = "omx_ultragoal"
    OMX_TEAM = "omx_team"
    OMX_RALPH = "omx_ralph"
    LOCAL = "local"
    PROMPT_ONLY = "prompt_only"


class CommandRecipe(StrictSchemaModel):
    """Represents one composed command recipe."""

    id: NonEmptyString
    source: CommandSource
    description: NonEmptyString
    risk: CommandRisk = CommandRisk.READ_ONLY
    steps: tuple["CommandStep", ...]

    @property
    def qualified_id(self) -> str:
        """Return source-qualified command id."""
        qualified_id: str = f"{self.source}:{self.id}"
        return qualified_id


class CommandStep(StrictSchemaModel):
    """Represents one step inside a composed command recipe."""

    command: CommandStepCommand
    agent: NonEmptyString | None = None
    argv: tuple[NonEmptyString, ...] = ()
    prompt_file: NonEmptyString | None = None
    inline_prompt: NonEmptyString | None = None
    brief_file: NonEmptyString | None = None
    output_last_message: NonEmptyString | None = None
    expected_artifacts: tuple[NonEmptyString, ...] = ()


class RepoCommandDefinition(StrictSchemaModel):
    """Represents one raw repo-defined command TOML table after validation."""

    description: NonEmptyString
    risk: CommandRisk = CommandRisk.READ_ONLY
    steps: tuple[CommandStep, ...] | None = None
    provider: NonEmptyString | None = None
    mode: NonEmptyString | None = None
    agent: NonEmptyString | None = None
    argv: tuple[NonEmptyString, ...] = ()
    prompt_file: NonEmptyString | None = None
    inline_prompt: NonEmptyString | None = None
    brief_file: NonEmptyString | None = None
    output_last_message: NonEmptyString | None = None
    expected_artifacts: tuple[NonEmptyString, ...] = ()


class CommandCatalog(StrictSchemaModel):
    """Represents the merged command catalog."""

    commands: tuple[CommandRecipe, ...] = ()

    @model_validator(mode="after")
    def _validate_duplicate_source_ids(self) -> "CommandCatalog":
        seen_ids: set[tuple[CommandSource, str]] = set()
        for recipe in self.commands:
            key = (recipe.source, recipe.id)
            if key in seen_ids:
                raise ValueError(f"duplicate command id in {recipe.source}: {recipe.id}")
            seen_ids.add(key)
        return self

    def find(self, command_id: str) -> CommandRecipe | None:
        """Find a command by qualified or unambiguous short id.

        Args:
            command_id [str]: Command id to find.

        Returns:
            CommandRecipe | None: Matching command when found and unambiguous.
        """
        if ":" in command_id:
            for recipe in self.commands:
                if recipe.qualified_id == command_id:
                    qualified_match: CommandRecipe = recipe
                    return qualified_match
            missing_qualified: None = None
            return missing_qualified

        matches: tuple[CommandRecipe, ...] = tuple(
            recipe for recipe in self.commands if recipe.id == command_id
        )
        if len(matches) == 1:
            short_match: CommandRecipe = matches[0]
            return short_match
        ambiguous_or_missing: None = None
        return ambiguous_or_missing


class CommandCatalogEntry(StrictSchemaModel):
    """Represents one command entry in list output."""

    id: NonEmptyString
    qualified_id: NonEmptyString
    source: CommandSource
    description: NonEmptyString
    risk: CommandRisk
    step_count: int = Field(ge=1)


class CommandCatalogListResult(StrictSchemaModel):
    """Represents `agent-remote commands list` output."""

    commands: tuple[CommandCatalogEntry, ...]
    builtin_count: int = Field(ge=0)
    repo_count: int = Field(ge=0)
    warnings: tuple[NonEmptyString, ...] = ()


class CommandShowResult(StrictSchemaModel):
    """Represents `agent-remote commands show` output."""

    recipe: CommandRecipe
    warnings: tuple[NonEmptyString, ...] = ()


class CommandPlanStep(StrictSchemaModel):
    """Represents one dry-run execution step."""

    index: int = Field(ge=1)
    command: CommandStepCommand
    agent: NonEmptyString | None = None
    native_argv: tuple[NonEmptyString, ...]
    prompt_file: NonEmptyString | None = None
    prompt_exists: bool | None = None
    prompt_sha256: NonEmptyString | None = None
    inline_prompt: NonEmptyString | None = None
    expected_artifacts: tuple[NonEmptyString, ...] = ()
    risk: CommandRisk
    blocked_reasons: tuple[NonEmptyString, ...] = ()


class CommandExecutionPlan(StrictSchemaModel):
    """Represents a composed-command dry-run plan."""

    command_id: NonEmptyString
    qualified_id: NonEmptyString
    source: CommandSource
    description: NonEmptyString
    risk: CommandRisk
    dry_run: bool
    steps: tuple[CommandPlanStep, ...]
    blocked_reasons: tuple[NonEmptyString, ...] = ()
