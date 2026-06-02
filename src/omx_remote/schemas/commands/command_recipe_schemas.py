from pydantic import Field, computed_field, model_validator

from omx_remote.adapter_types.json_types import JsonObject
from omx_remote.schemas.commands.command_role_schemas import CommandRoleLane
from omx_remote.schemas.commands.command_runtime_option_schemas import (
    CommandRuntimeOptions,
)
from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel
from omx_remote.shared.omx_enums.command_enums import (
    CodexSandboxMode,
    CommandNamespace,
    CommandRecipeCategory,
    CommandRecipeMode,
    CommandRecipeProvider,
    CommandRisk,
    CommandSource,
    CommandStepCommand,
)


class CommandRecipe(StrictSchemaModel):
    """Represents one composed command recipe."""

    id: NonEmptyString
    source: CommandSource
    description: NonEmptyString
    namespace: CommandNamespace = CommandNamespace.WORKFLOW
    category: CommandRecipeCategory = CommandRecipeCategory.CUSTOM
    risk: CommandRisk = CommandRisk.READ_ONLY
    steps: tuple["CommandStep", ...]

    @model_validator(mode="after")
    def _validate_namespace_local_id(self) -> "CommandRecipe":
        """Ensure namespace-owned recipes keep namespace out of the local id.

        Returns:
            CommandRecipe: Validated command recipe.
        """
        adapter_ops_prefixes: tuple[str, str, str] = (
            f"{CommandNamespace.ADAPTER_OPS}:",
            f"{CommandNamespace.ADAPTER_OPS}/",
            f"{CommandNamespace.ADAPTER_OPS} ",
        )
        has_adapter_ops_prefix = self.id.startswith(adapter_ops_prefixes)
        if self.namespace == CommandNamespace.ADAPTER_OPS and has_adapter_ops_prefix:
            raise ValueError("adapter-ops recipe id must be namespace-local")
        if self.namespace != CommandNamespace.ADAPTER_OPS and has_adapter_ops_prefix:
            raise ValueError("adapter-ops command id prefix is namespace-reserved")
        return self

    @computed_field
    @property
    def public_id(self) -> str:
        """Return the machine-stable command id.

        Returns:
            str: Namespace-qualified public id when the namespace is command-like.
        """
        if self.namespace == CommandNamespace.ADAPTER_OPS:
            public_id = f"{CommandNamespace.ADAPTER_OPS}:{self.id}"
            return public_id
        public_id: str = self.id
        return public_id

    @computed_field
    @property
    def display_id(self) -> str:
        """Return the user-facing command id shown in CLI and docs.

        Returns:
            str: Display id, using space-form adapter-ops namespace routing.
        """
        if self.namespace == CommandNamespace.ADAPTER_OPS:
            display_id = f"{CommandNamespace.ADAPTER_OPS} {self.id}"
            return display_id
        display_id: str = self.public_id
        return display_id

    @property
    def qualified_id(self) -> str:
        """Return source-qualified machine-stable command id.

        Returns:
            str: Command id prefixed by its recipe source.
        """
        qualified_id: str = f"{self.source}:{self.public_id}"
        return qualified_id

    @computed_field
    @property
    def display_qualified_id(self) -> str:
        """Return source-qualified user-facing command id.

        Returns:
            str: Display id prefixed by its recipe source.
        """
        display_qualified_id: str = f"{self.source}:{self.display_id}"
        return display_qualified_id

    def matches_id(self, command_id: str) -> bool:
        """Return whether a caller-supplied id addresses this recipe.

        Args:
            command_id [str]: Short or source-qualified command id.

        Returns:
            bool: Whether the id matches machine-stable or display routing.
        """
        known_ids = {
            self.public_id,
            self.qualified_id,
            self.display_id,
            self.display_qualified_id,
        }
        matches: bool = command_id in known_ids
        return matches


class CommandStep(StrictSchemaModel):
    """Represents one step inside a composed command recipe."""

    command: CommandStepCommand
    agent: NonEmptyString | None = None
    argv: tuple[NonEmptyString, ...] = ()
    codex_search: bool = False
    codex_sandbox: CodexSandboxMode | None = None
    prompt_file: NonEmptyString | None = None
    inline_prompt: NonEmptyString | None = None
    brief_file: NonEmptyString | None = None
    mcp_server: NonEmptyString | None = None
    mcp_tool: NonEmptyString | None = None
    mcp_arguments: JsonObject = Field(default_factory=dict)
    output_last_message: NonEmptyString | None = None
    expected_artifacts: tuple[NonEmptyString, ...] = ()
    role_lanes: tuple[CommandRoleLane, ...] = ()

    @model_validator(mode="after")
    def _validate_codex_options(self) -> "CommandStep":
        """Ensure Codex-only options stay on Codex execution steps.

        Returns:
            CommandStep: Validated command step.
        """
        if self.command == CommandStepCommand.CODEX_EXEC:
            return self
        if self.codex_search or self.codex_sandbox is not None:
            raise ValueError(
                "codex_search and codex_sandbox require command=codex_exec"
            )
        return self


class RepoCommandDefinition(StrictSchemaModel):
    """Represents one raw repo-defined command TOML table after validation."""

    description: NonEmptyString
    risk: CommandRisk = CommandRisk.READ_ONLY
    steps: tuple[CommandStep, ...] | None = None
    provider: CommandRecipeProvider | None = None
    mode: CommandRecipeMode | None = None
    agent: NonEmptyString | None = None
    argv: tuple[NonEmptyString, ...] = ()
    codex_search: bool = False
    codex_sandbox: CodexSandboxMode | None = None
    prompt_file: NonEmptyString | None = None
    inline_prompt: NonEmptyString | None = None
    brief_file: NonEmptyString | None = None
    mcp_server: NonEmptyString | None = None
    mcp_tool: NonEmptyString | None = None
    mcp_arguments: JsonObject = Field(default_factory=dict)
    output_last_message: NonEmptyString | None = None
    expected_artifacts: tuple[NonEmptyString, ...] = ()
    role_lanes: tuple[CommandRoleLane, ...] = ()

    @model_validator(mode="after")
    def _validate_codex_options(self) -> "RepoCommandDefinition":
        """Ensure shorthand Codex options stay on Codex execution definitions.

        Returns:
            RepoCommandDefinition: Validated repo command definition.
        """
        if not self.codex_search and self.codex_sandbox is None:
            return self
        if self.steps is not None:
            raise ValueError(
                "top-level codex_search/codex_sandbox cannot be combined with steps"
            )
        if (
            self.provider == CommandRecipeProvider.CODEX
            and self.mode == CommandRecipeMode.EXEC
        ):
            return self
        raise ValueError(
            "codex_search and codex_sandbox require provider='codex' and mode='exec'"
        )


class CommandCatalog(StrictSchemaModel):
    """Represents the merged command catalog."""

    commands: tuple[CommandRecipe, ...] = ()

    @model_validator(mode="after")
    def _validate_duplicate_source_ids(self) -> "CommandCatalog":
        """Reject duplicate command ids from the same source.

        Returns:
            CommandCatalog: Validated command catalog.
        """
        seen_ids: set[tuple[CommandSource, str]] = set()
        for recipe in self.commands:
            key = (recipe.source, recipe.public_id)
            if key in seen_ids:
                raise ValueError(
                    f"duplicate command id in {recipe.source}: {recipe.public_id}"
                )
            seen_ids.add(key)
        return self

    def find(self, command_id: str) -> CommandRecipe | None:
        """Find a command by qualified or unambiguous short id.

        Args:
            command_id [str]: Command id to find.

        Returns:
            CommandRecipe | None: Matching command when found and unambiguous.
        """
        if ":" in command_id and command_id.split(":", maxsplit=1)[0] in {
            source.value for source in CommandSource
        }:
            for recipe in self.commands:
                if recipe.matches_id(command_id):
                    qualified_match: CommandRecipe = recipe
                    return qualified_match
            missing_qualified: None = None
            return missing_qualified

        matches: tuple[CommandRecipe, ...] = tuple(
            recipe for recipe in self.commands if recipe.matches_id(command_id)
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
    machine_id: NonEmptyString
    machine_qualified_id: NonEmptyString
    source: CommandSource
    namespace: CommandNamespace
    category: CommandRecipeCategory
    description: NonEmptyString
    risk: CommandRisk
    step_count: int = Field(ge=1)


class CommandCatalogListResult(StrictSchemaModel):
    """Represents `comx-agent commands list` output."""

    commands: tuple[CommandCatalogEntry, ...]
    builtin_count: int = Field(ge=0)
    repo_count: int = Field(ge=0)
    public_workflow_commands: int = Field(ge=0)
    lifecycle_commands: int = Field(ge=0)
    macro_commands: int = Field(ge=0)
    adapter_ops_commands: int = Field(ge=0)
    warnings: tuple[NonEmptyString, ...] = ()


class CommandShowResult(StrictSchemaModel):
    """Represents `comx-agent commands show` output."""

    recipe: CommandRecipe
    warnings: tuple[NonEmptyString, ...] = ()


class CommandPlanStep(StrictSchemaModel):
    """Represents one dry-run execution step."""

    index: int = Field(ge=1)
    command: CommandStepCommand
    agent: NonEmptyString | None = None
    native_argv: tuple[NonEmptyString, ...]
    codex_search: bool = False
    codex_sandbox: CodexSandboxMode | None = None
    prompt_file: NonEmptyString | None = None
    prompt_exists: bool | None = None
    prompt_sha256: NonEmptyString | None = None
    inline_prompt: NonEmptyString | None = None
    mcp_server: NonEmptyString | None = None
    mcp_tool: NonEmptyString | None = None
    mcp_arguments: JsonObject = Field(default_factory=dict)
    expected_artifacts: tuple[NonEmptyString, ...] = ()
    role_lanes: tuple[CommandRoleLane, ...] = ()
    risk: CommandRisk
    blocked_reasons: tuple[NonEmptyString, ...] = ()


class CommandExecutionPlan(StrictSchemaModel):
    """Represents a composed-command dry-run plan."""

    command_id: NonEmptyString
    qualified_id: NonEmptyString
    source: CommandSource
    namespace: CommandNamespace
    category: CommandRecipeCategory
    description: NonEmptyString
    risk: CommandRisk
    dry_run: bool
    runtime_options: CommandRuntimeOptions | None = None
    steps: tuple[CommandPlanStep, ...]
    blocked_reasons: tuple[NonEmptyString, ...] = ()
