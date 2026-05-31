from pydantic import Field, computed_field, model_validator

from omx_remote.adapter_types.json_types import JsonObject
from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel
from omx_remote.shared.omx_enums.mcp_enums import McpServerSource, McpTransportKind


class McpEnvironmentVariable(StrictSchemaModel):
    """Represents one environment entry for a stdio MCP server."""

    name: NonEmptyString
    value: str | None = None


class McpServerTransport(StrictSchemaModel):
    """Represents the transport configuration needed to reach an MCP server."""

    type: McpTransportKind
    command: NonEmptyString | None = None
    args: tuple[NonEmptyString, ...] = ()
    env: tuple[McpEnvironmentVariable, ...] = ()
    env_vars: tuple[NonEmptyString, ...] = ()
    cwd: NonEmptyString | None = None
    url: NonEmptyString | None = None
    bearer_token_env_var: NonEmptyString | None = None

    @model_validator(mode="after")
    def _validate_transport_target(self) -> "McpServerTransport":
        """Require the target field that belongs to the selected transport.

        Returns:
            McpServerTransport: Validated transport.
        """
        if self.type == McpTransportKind.STDIO and self.command is None:
            raise ValueError("stdio MCP transport requires command")
        if self.type == McpTransportKind.STREAMABLE_HTTP and self.url is None:
            raise ValueError("streamable_http MCP transport requires url")
        return self


class McpServerConfig(StrictSchemaModel):
    """Represents one MCP server that comx-agent can consume as a client."""

    name: NonEmptyString
    source: McpServerSource
    enabled: bool
    transport: McpServerTransport
    startup_timeout_sec: float | None = Field(default=None, gt=0)
    tool_timeout_sec: float | None = Field(default=None, gt=0)
    auth_status: NonEmptyString | None = None
    disabled_reason: NonEmptyString | None = None

    @computed_field
    @property
    def qualified_name(self) -> str:
        """Return source-qualified server name.

        Returns:
            str: Name prefixed by source.
        """
        qualified_name: str = f"{self.source}:{self.name}"
        return qualified_name


class RepoMcpServerDefinition(StrictSchemaModel):
    """Represents one repo-local MCP server config after TOML validation."""

    enabled: bool = True
    transport: McpTransportKind | None = None
    command: NonEmptyString | None = None
    args: tuple[NonEmptyString, ...] = ()
    env: dict[NonEmptyString, str] = Field(default_factory=dict)
    env_vars: tuple[NonEmptyString, ...] = ()
    cwd: NonEmptyString | None = None
    url: NonEmptyString | None = None
    bearer_token_env_var: NonEmptyString | None = None
    startup_timeout_sec: float | None = Field(default=None, gt=0)
    tool_timeout_sec: float | None = Field(default=None, gt=0)


class McpServerListResult(StrictSchemaModel):
    """Represents the discovered MCP server registry."""

    servers: tuple[McpServerConfig, ...]
    codex_count: int = Field(ge=0)
    repo_count: int = Field(ge=0)
    enabled_count: int = Field(ge=0)
    warnings: tuple[NonEmptyString, ...] = ()


class McpToolDescriptor(StrictSchemaModel):
    """Represents one MCP tool advertised by a connected server."""

    server_name: NonEmptyString
    server_source: McpServerSource
    name: NonEmptyString
    title: NonEmptyString | None = None
    description: NonEmptyString | None = None
    input_schema: JsonObject | None = None
    output_schema: JsonObject | None = None


class McpToolListResult(StrictSchemaModel):
    """Represents the tools advertised by one MCP server."""

    server: McpServerConfig
    tools: tuple[McpToolDescriptor, ...]
    warnings: tuple[NonEmptyString, ...] = ()


class McpToolCallPlan(StrictSchemaModel):
    """Represents a safe dry-run MCP tool call plan."""

    server: McpServerConfig
    tool_name: NonEmptyString
    arguments: JsonObject = Field(default_factory=dict)
    execute_required: bool = True
    warnings: tuple[NonEmptyString, ...] = ()


class McpToolCallResult(StrictSchemaModel):
    """Represents the result of an executed MCP tool call."""

    server: McpServerConfig
    tool_name: NonEmptyString
    arguments: JsonObject = Field(default_factory=dict)
    executed: bool
    result: JsonObject | None = None
    warnings: tuple[NonEmptyString, ...] = ()


class McpServerRegistrationResult(StrictSchemaModel):
    """Represents one repo-local MCP server registration write."""

    server: McpServerConfig
    config_path: NonEmptyString
    created_config: bool
    replaced_existing: bool
    warnings: tuple[NonEmptyString, ...] = ()


class McpServerRemovalResult(StrictSchemaModel):
    """Represents removal of one repo-local MCP server registration."""

    server_name: NonEmptyString
    config_path: NonEmptyString
    removed: bool
    warnings: tuple[NonEmptyString, ...] = ()
