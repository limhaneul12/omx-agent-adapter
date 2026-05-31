from omx_remote.schemas.mcp.client_schemas import (
    McpTransportKind,
    RepoMcpServerDefinition,
)


def infer_repo_mcp_transport_kind(
    definition: RepoMcpServerDefinition,
) -> McpTransportKind:
    """Infer the effective transport kind for a repo-defined MCP server.

    Args:
        definition [RepoMcpServerDefinition]: Server definition from repo config or CLI.

    Returns:
        McpTransportKind: Explicit or inferred MCP transport kind.
    """
    if definition.transport is not None:
        transport_kind: McpTransportKind = definition.transport
        return transport_kind
    if definition.url is not None:
        transport_kind = McpTransportKind.STREAMABLE_HTTP
        return transport_kind
    transport_kind = McpTransportKind.STDIO
    return transport_kind
