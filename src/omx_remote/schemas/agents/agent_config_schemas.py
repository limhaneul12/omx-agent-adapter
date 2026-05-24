from enum import StrEnum

from pydantic import Field, field_validator

from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel


class AgentProvider(StrEnum):
    """Supported subagent configuration providers."""

    CODEX = "codex"


class AgentEffort(StrEnum):
    """Supported reasoning effort labels for configured subagents."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"


class AgentConfig(StrictSchemaModel):
    """Represents one TOML-defined agent configuration."""

    id: NonEmptyString
    enabled: bool
    provider: AgentProvider
    role: NonEmptyString
    model: NonEmptyString
    effort: AgentEffort
    persona: NonEmptyString
    routing_hints: tuple[NonEmptyString, ...] = ()

    @field_validator("id")
    @classmethod
    def _validate_filesystem_safe_id(cls, value: str) -> str:
        """Validate that agent ids are safe generated-file names.

        Args:
            value [str]: Agent id from TOML.

        Returns:
            str: Filesystem-safe agent id.
        """
        allowed_characters: set[str] = {"-", "_"}
        if not value[0].isalnum() or not all(
            character.isalnum() or character in allowed_characters
            for character in value
        ):
            raise ValueError(
                "agent id must be filesystem-safe: start with a letter or digit "
                "and use only letters, digits, '-' or '_'"
            )
        return value


class AgentConfigSet(StrictSchemaModel):
    """Represents the loaded repo-local agent configuration set."""

    config_path: NonEmptyString
    agents: tuple[AgentConfig, ...] = ()
    warnings: tuple[NonEmptyString, ...] = ()

    @property
    def enabled_agents(self) -> tuple[AgentConfig, ...]:
        """Return enabled agents in config order.

        Returns:
            tuple[AgentConfig, ...]: Enabled agents preserving source order.
        """
        enabled_agents: tuple[AgentConfig, ...] = tuple(
            agent for agent in self.agents if agent.enabled
        )
        return enabled_agents

    def find_agent(self, agent_id: str) -> AgentConfig | None:
        """Find one configured agent by id.

        Args:
            agent_id [str]: Configured agent id to find.

        Returns:
            AgentConfig | None: Matching configured agent when present.
        """
        for agent in self.agents:
            if agent.id == agent_id:
                found_agent: AgentConfig = agent
                return found_agent
        missing_agent: None = None
        return missing_agent


class AgentListResult(StrictSchemaModel):
    """Represents `agent-remote agents list` output."""

    config_path: NonEmptyString
    agents: tuple[AgentConfig, ...]
    enabled_count: int = Field(ge=0)
    disabled_count: int = Field(ge=0)
    warnings: tuple[NonEmptyString, ...] = ()


class AgentShowResult(StrictSchemaModel):
    """Represents `agent-remote agents show` output."""

    config_path: NonEmptyString
    agent: AgentConfig
    warnings: tuple[NonEmptyString, ...] = ()


class AgentValidationResult(StrictSchemaModel):
    """Represents `agent-remote agents validate` output."""

    valid: bool
    config_path: NonEmptyString
    agent_count: int = Field(ge=0)
    warnings: tuple[NonEmptyString, ...] = ()
    error: str | None = None
