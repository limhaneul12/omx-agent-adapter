import subprocess
from collections.abc import Sequence

import orjson

from omx_remote.adapter_types.json_types import JsonObject, JsonValue
from omx_remote.runtime.mcp.mcp_json_payloads import (
    normalize_mcp_json_object,
    normalize_mcp_json_object_list,
)
from omx_remote.schemas.mcp.client_schemas import (
    McpEnvironmentVariable,
    McpServerConfig,
    McpServerSource,
    McpServerTransport,
    McpTransportKind,
)


class CodexMcpRegistryError(ValueError):
    """Raised when the Codex MCP registry cannot be read or normalized."""


def _json_list(value: object) -> list[JsonObject]:
    """Round-trip a dynamic payload into a list of JSON objects.

    Args:
        value [object]: Dynamic payload from a process boundary.

    Returns:
        list[JsonObject]: JSON-compatible object list.
    """
    try:
        objects = normalize_mcp_json_object_list(
            value,
            "Codex MCP list output must contain JSON objects.",
        )
    except ValueError as error:
        raise CodexMcpRegistryError(str(error)) from error
    return objects


def _string_tuple(value: JsonValue | None) -> tuple[str, ...]:
    """Normalize a JSON list of strings into an immutable tuple.

    Args:
        value [JsonValue | None]: Candidate JSON value.

    Returns:
        tuple[str, ...]: String tuple.
    """
    if value is None:
        empty: tuple[str, ...] = ()
        return empty
    if not isinstance(value, list):
        raise CodexMcpRegistryError(
            "Expected a list of strings in Codex MCP transport."
        )

    values: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise CodexMcpRegistryError(
                "Expected only strings in Codex MCP transport list."
            )
        values.append(item)

    normalized_values: tuple[str, ...] = tuple(values)
    return normalized_values


def _env_tuple(
    env_value: JsonValue | None, env_vars_value: JsonValue | None
) -> tuple[McpEnvironmentVariable, ...]:
    """Normalize Codex MCP env payloads into typed environment entries.

    Args:
        env_value [JsonValue | None]: Optional env object with concrete values.
        env_vars_value [JsonValue | None]: Optional env var name list.

    Returns:
        tuple[McpEnvironmentVariable, ...]: Typed environment entries.
    """
    entries: dict[str, str | None] = {}
    if isinstance(env_value, dict):
        for name, value in env_value.items():
            entries[name] = None if value is None else str(value)
    elif env_value is not None:
        raise CodexMcpRegistryError(
            "Codex MCP transport env must be an object or null."
        )

    if isinstance(env_vars_value, list):
        for item in env_vars_value:
            if not isinstance(item, str):
                raise CodexMcpRegistryError("Codex MCP env_vars must contain strings.")
            entries.setdefault(item, None)
    elif env_vars_value is not None:
        raise CodexMcpRegistryError(
            "Codex MCP transport env_vars must be a list or null."
        )

    env_entries: tuple[McpEnvironmentVariable, ...] = tuple(
        McpEnvironmentVariable(name=name, value=value)
        for name, value in sorted(entries.items())
    )
    return env_entries


def _transport_from_payload(payload: JsonObject) -> McpServerTransport:
    """Normalize one Codex MCP transport object.

    Args:
        payload [JsonObject]: Transport JSON object from `codex mcp list --json`.

    Returns:
        McpServerTransport: Typed transport config.
    """
    transport_type_value: JsonValue | None = payload.get("type")
    if transport_type_value == "stdio":
        command_value: JsonValue | None = payload.get("command")
        if not isinstance(command_value, str):
            raise CodexMcpRegistryError("Codex stdio MCP transport requires command.")
        transport = McpServerTransport(
            type=McpTransportKind.STDIO,
            command=command_value,
            args=_string_tuple(payload.get("args")),
            env=_env_tuple(payload.get("env"), payload.get("env_vars")),
            env_vars=_string_tuple(payload.get("env_vars")),
            cwd=None if payload.get("cwd") is None else str(payload.get("cwd")),
        )
        return transport

    if transport_type_value in {"streamable_http", "http"}:
        url_value: JsonValue | None = payload.get("url")
        if not isinstance(url_value, str):
            raise CodexMcpRegistryError("Codex HTTP MCP transport requires url.")
        bearer_token_env_var: str | None = None
        raw_bearer_value: JsonValue | None = payload.get("bearer_token_env_var")
        if raw_bearer_value is not None:
            bearer_token_env_var = str(raw_bearer_value)
        transport = McpServerTransport(
            type=McpTransportKind.STREAMABLE_HTTP,
            url=url_value,
            bearer_token_env_var=bearer_token_env_var,
        )
        return transport

    raise CodexMcpRegistryError(
        f"Unsupported Codex MCP transport type: {transport_type_value!r}"
    )


def _optional_positive_float(value: JsonValue | None, field_name: str) -> float | None:
    """Normalize an optional JSON scalar into a float.

    Args:
        value [JsonValue | None]: Candidate value.
        field_name [str]: Field name for diagnostics.

    Returns:
        float | None: Normalized float when present.
    """
    if value is None:
        missing_value: None = None
        return missing_value
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        raise CodexMcpRegistryError(f"Codex MCP {field_name} must be numeric when set.")

    normalized_value: float = float(value)
    return normalized_value


def server_from_codex_payload(payload: JsonObject) -> McpServerConfig:
    """Normalize one Codex MCP registry server object.

    Args:
        payload [JsonObject]: Server object from `codex mcp list --json`.

    Returns:
        McpServerConfig: Typed MCP server config.
    """
    name_value: JsonValue | None = payload.get("name")
    if not isinstance(name_value, str):
        raise CodexMcpRegistryError("Codex MCP server payload requires name.")

    transport_value: JsonValue | None = payload.get("transport")
    if not isinstance(transport_value, dict):
        raise CodexMcpRegistryError(
            "Codex MCP server payload requires transport object."
        )
    try:
        transport_payload: JsonObject = normalize_mcp_json_object(
            transport_value,
            "Expected a JSON object while reading Codex MCP data.",
        )
    except ValueError as error:
        raise CodexMcpRegistryError(str(error)) from error

    enabled_value: JsonValue | None = payload.get("enabled")
    if not isinstance(enabled_value, bool):
        raise CodexMcpRegistryError(
            "Codex MCP server payload requires boolean enabled."
        )
    enabled: bool = enabled_value
    startup_timeout_value: JsonValue | None = payload.get("startup_timeout_sec")
    tool_timeout_value: JsonValue | None = payload.get("tool_timeout_sec")
    disabled_reason_value: JsonValue | None = payload.get("disabled_reason")
    auth_status_value: JsonValue | None = payload.get("auth_status")
    server = McpServerConfig(
        name=name_value,
        source=McpServerSource.CODEX,
        enabled=enabled,
        transport=_transport_from_payload(transport_payload),
        startup_timeout_sec=_optional_positive_float(
            startup_timeout_value,
            "startup_timeout_sec",
        ),
        tool_timeout_sec=_optional_positive_float(
            tool_timeout_value,
            "tool_timeout_sec",
        ),
        disabled_reason=None
        if disabled_reason_value is None
        else str(disabled_reason_value),
        auth_status=None if auth_status_value is None else str(auth_status_value),
    )
    return server


def servers_from_codex_payload(payload: object) -> tuple[McpServerConfig, ...]:
    """Normalize `codex mcp list --json` output.

    Args:
        payload [object]: Decoded JSON payload.

    Returns:
        tuple[McpServerConfig, ...]: Typed server configs.
    """
    server_payloads: list[JsonObject] = _json_list(payload)
    servers: tuple[McpServerConfig, ...] = tuple(
        server_from_codex_payload(server_payload) for server_payload in server_payloads
    )
    return servers


def read_codex_mcp_servers(
    command: Sequence[str] = ("codex", "mcp", "list", "--json"),
) -> tuple[McpServerConfig, ...]:
    """Read MCP server configs from Codex's own MCP registry.

    Args:
        command [Sequence[str]]: Command used to query Codex.

    Returns:
        tuple[McpServerConfig, ...]: Codex-configured server configs.
    """
    try:
        completed_process = subprocess.run(
            tuple(command),
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as error:
        raise CodexMcpRegistryError(
            f"Could not run codex MCP registry command: {error}"
        ) from error

    if completed_process.returncode != 0:
        stderr: str = completed_process.stderr.strip()
        raise CodexMcpRegistryError(
            f"codex MCP registry command failed with exit {completed_process.returncode}: {stderr}"
        )

    try:
        decoded_payload: object = orjson.loads(completed_process.stdout)
    except orjson.JSONDecodeError as error:
        raise CodexMcpRegistryError(
            "codex MCP registry command did not return valid JSON."
        ) from error

    servers: tuple[McpServerConfig, ...] = servers_from_codex_payload(decoded_payload)
    return servers
