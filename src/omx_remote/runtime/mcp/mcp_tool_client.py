from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta

import httpx
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

from mcp import ClientSession, StdioServerParameters
from omx_remote.adapter_types.json_types import JsonObject
from omx_remote.runtime.mcp.mcp_json_payloads import normalize_mcp_json_object
from omx_remote.schemas.mcp_client_schemas import (
    McpServerConfig,
    McpToolCallResult,
    McpToolDescriptor,
    McpToolListResult,
    McpTransportKind,
)
from omx_remote.shared.process_environment_settings import ProcessEnvironmentSettings


class McpToolClientError(ValueError):
    """Raised when an MCP client operation cannot be completed safely."""


def _json_object_from_model(value: object) -> JsonObject:
    """Convert a third-party model/dynamic value into a JSON object.

    Args:
        value [object]: Dynamic SDK value.

    Returns:
        JsonObject: JSON-compatible object.
    """
    try:
        json_object = normalize_mcp_json_object(
            value,
            "Expected MCP SDK payload to normalize to JSON object.",
        )
    except ValueError as error:
        raise McpToolClientError(str(error)) from error
    return json_object


def _optional_json_object(value: object | None) -> JsonObject | None:
    """Normalize an optional dynamic object into a JSON object.

    Args:
        value [object | None]: Candidate dynamic object.

    Returns:
        JsonObject | None: Normalized object when provided.
    """
    if value is None:
        missing_object: None = None
        return missing_object
    json_object: JsonObject = _json_object_from_model(value)
    return json_object


def _stdio_env(server: McpServerConfig) -> dict[str, str] | None:
    """Build an environment for a stdio MCP server process.

    Args:
        server [McpServerConfig]: MCP server config.

    Returns:
        dict[str, str] | None: Environment override or None to inherit.
    """
    environment_settings = ProcessEnvironmentSettings()
    environment_values = environment_settings.environment_values
    concrete_entries: dict[str, str] = {
        entry.name: entry.value
        for entry in server.transport.env
        if entry.value is not None
    }
    inherited_names: set[str] = {
        entry.name
        for entry in server.transport.env
        if entry.value is None and entry.name in environment_values
    }
    if not concrete_entries and not inherited_names:
        inherited_environment: None = None
        return inherited_environment

    env: dict[str, str] = dict(environment_values)
    env.update(concrete_entries)
    for name in inherited_names:
        env[name] = environment_values[name]
    return env


def _bearer_headers(server: McpServerConfig) -> dict[str, str]:
    """Build HTTP bearer headers for streamable HTTP MCP when configured.

    Args:
        server [McpServerConfig]: MCP server config.

    Returns:
        dict[str, str]: HTTP headers for the MCP client.
    """
    token_env_var: str | None = server.transport.bearer_token_env_var
    if token_env_var is None:
        empty_headers: dict[str, str] = {}
        return empty_headers

    environment_settings = ProcessEnvironmentSettings()
    token_value: str | None = environment_settings.dynamic_environment_value(
        token_env_var
    )
    if not token_value:
        raise McpToolClientError(
            f"MCP bearer token environment variable {token_env_var} is not set."
        )

    headers: dict[str, str] = {"Authorization": f"Bearer {token_value}"}
    return headers


@asynccontextmanager
async def _open_client_session(
    server: McpServerConfig,
) -> AsyncIterator[ClientSession]:
    """Open an MCP ClientSession for the configured transport.

    Args:
        server [McpServerConfig]: MCP server config.

    Yields:
        object: Initialized MCP ClientSession.

    Returns:
        AsyncIterator[ClientSession]: Async context manager iterator.
    """
    timeout: timedelta | None = None
    if server.tool_timeout_sec is not None:
        timeout = timedelta(seconds=server.tool_timeout_sec)

    if server.transport.type == McpTransportKind.STDIO:
        if server.transport.command is None:
            raise McpToolClientError("stdio MCP transport requires command.")
        server_params = StdioServerParameters(
            command=server.transport.command,
            args=list(server.transport.args),
            env=_stdio_env(server),
            cwd=server.transport.cwd,
        )
        async with (
            stdio_client(server_params) as (
                read_stream,
                write_stream,
            ),
            ClientSession(
                read_stream,
                write_stream,
                read_timeout_seconds=timeout,
            ) as session,
        ):
            await session.initialize()
            yield session
        return

    if server.transport.type == McpTransportKind.STREAMABLE_HTTP:
        if server.transport.url is None:
            raise McpToolClientError("streamable_http MCP transport requires url.")
        http_headers: dict[str, str] = _bearer_headers(server)
        async with (
            httpx.AsyncClient(headers=http_headers) as http_client,
            streamable_http_client(
                server.transport.url,
                http_client=http_client,
            ) as (
                read_stream,
                write_stream,
                _get_session_id,
            ),
            ClientSession(
                read_stream,
                write_stream,
                read_timeout_seconds=timeout,
            ) as session,
        ):
            await session.initialize()
            yield session
        return

    raise McpToolClientError(f"Unsupported MCP transport: {server.transport.type}")


async def list_mcp_tools(server: McpServerConfig) -> McpToolListResult:
    """Connect to one MCP server and list advertised tools.

    Args:
        server [McpServerConfig]: MCP server config.

    Returns:
        McpToolListResult: Tool metadata.
    """
    async with _open_client_session(server) as session:
        tools_response = await session.list_tools()

    tools: list[McpToolDescriptor] = []
    for tool in tools_response.tools:
        tool_payload: JsonObject = _json_object_from_model(
            tool.model_dump(by_alias=True)
        )
        input_schema: JsonObject | None = _optional_json_object(
            tool_payload.get("inputSchema")
        )
        output_schema: JsonObject | None = _optional_json_object(
            tool_payload.get("outputSchema")
        )
        descriptor = McpToolDescriptor(
            server_name=server.name,
            server_source=server.source,
            name=str(tool_payload["name"]),
            title=None
            if tool_payload.get("title") is None
            else str(tool_payload["title"]),
            description=None
            if tool_payload.get("description") is None
            else str(tool_payload["description"]),
            input_schema=input_schema,
            output_schema=output_schema,
        )
        tools.append(descriptor)

    result = McpToolListResult(server=server, tools=tuple(tools))
    return result


async def call_mcp_tool(
    server: McpServerConfig,
    tool_name: str,
    arguments: JsonObject,
) -> McpToolCallResult:
    """Connect to one MCP server and call one tool.

    Args:
        server [McpServerConfig]: MCP server config.
        tool_name [str]: Tool name to invoke.
        arguments [JsonObject]: JSON-compatible tool arguments.

    Returns:
        McpToolCallResult: Tool call result.
    """
    async with _open_client_session(server) as session:
        call_result = await session.call_tool(tool_name, arguments=arguments)

    result_payload: JsonObject = _json_object_from_model(
        call_result.model_dump(by_alias=True)
    )
    result = McpToolCallResult(
        server=server,
        tool_name=tool_name,
        arguments=arguments,
        executed=True,
        result=result_payload,
    )
    return result
