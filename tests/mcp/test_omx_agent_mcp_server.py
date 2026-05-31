import asyncio
from collections.abc import Sequence
from pathlib import Path

import orjson
from mcp.types import ContentBlock, TextContent

from omx_remote.runtime.mcp.omx_agent_command_tools import preview_command_tool_payload
from omx_remote.runtime.mcp.omx_agent_mcp_server import build_omx_agent_mcp_server


def _text_payload(
    blocks: Sequence[ContentBlock] | dict[str, object],
) -> dict[str, object]:
    assert isinstance(blocks, Sequence)
    first = blocks[0]
    if isinstance(first, Sequence) and not isinstance(first, TextContent):
        nested_first = first[0]
        assert isinstance(nested_first, TextContent)
        payload = orjson.loads(nested_first.text)
    else:
        assert isinstance(first, TextContent)
        payload = orjson.loads(first.text)
    assert isinstance(payload, dict)
    return payload


def test_preview_command_tool_payload_injects_objective(tmp_path: Path) -> None:
    payload = preview_command_tool_payload(
        cwd=tmp_path,
        command_id="builtin:codex-deep-research",
        objective="Find the safest MCP shape for omx-agent custom commands.",
    )

    assert payload["ok"] is True
    assert payload["command_id"] == "codex-deep-research"
    plan = payload["plan"]
    assert isinstance(plan, dict)
    first_step = plan["steps"][0]
    assert first_step["codex_search"] is True
    assert "MCP tool-supplied context" in first_step["inline_prompt"]
    assert "safest MCP shape" in first_step["inline_prompt"]


def test_preview_command_tool_payload_supports_new_dogfood_commands(
    tmp_path: Path,
) -> None:
    payload = preview_command_tool_payload(
        cwd=tmp_path,
        command_id="builtin:route-doctor",
        objective="Pick the safest route for implementing dogfood commands.",
    )

    assert payload["ok"] is True
    assert payload["command_id"] == "route-doctor"
    plan = payload["plan"]
    assert isinstance(plan, dict)
    assert plan["risk"] == "read_only"
    final_step = plan["steps"][-1]
    assert "dogfood commands" in final_step["inline_prompt"]


def test_omx_agent_mcp_server_advertises_custom_workflow_tools() -> None:
    async def run_check() -> list[str]:
        server = build_omx_agent_mcp_server(cwd=".")
        tools = await server.list_tools()
        names = [tool.name for tool in tools]
        return names

    tool_names = asyncio.run(run_check())

    assert "omx_agent_preview_command" in tool_names
    assert "codex_deep_research" in tool_names
    assert "omx_autoresearch_loop" in tool_names
    assert "research_interview_prd" in tool_names
    assert "company_build_loop" not in tool_names
    assert "verify_handoff_plus" in tool_names


def test_omx_agent_mcp_server_tool_call_returns_typed_plan(tmp_path: Path) -> None:
    async def run_call() -> dict[str, object]:
        server = build_omx_agent_mcp_server(cwd=tmp_path)
        result = await server.call_tool(
            "research_interview_prd",
            {"objective": "Design an agent-friendly MCP interface."},
        )
        payload = _text_payload(result)
        return payload

    payload = asyncio.run(run_call())

    assert payload["ok"] is True
    assert payload["qualified_id"] == "builtin:research-interview-prd"
    plan = payload["plan"]
    assert isinstance(plan, dict)
    assert plan["risk"] == "long_running"
    first_step = plan["steps"][0]
    assert "agent-friendly MCP interface" in first_step["inline_prompt"]
    assert payload["warnings"] == [
        "MCP tool returns a dry-run plan only; it does not execute native Codex/OMX commands."
    ]
