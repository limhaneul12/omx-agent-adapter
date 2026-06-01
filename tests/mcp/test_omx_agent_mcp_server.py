import asyncio
import shlex
from collections.abc import Sequence
from pathlib import Path

import orjson
import pytest
from mcp.types import ContentBlock, TextContent

from omx_remote.runtime.mcp.omx_agent_command_tools import (
    CommandCatalogResolutionError,
    list_command_tools_payload,
    preview_command_tool_payload,
    show_command_tool_payload,
)
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


def test_list_command_tools_payload_groups_nine_public_workflows(
    tmp_path: Path,
) -> None:
    payload = list_command_tools_payload(cwd=tmp_path)

    assert payload["ok"] is True
    catalog = payload["catalog"]
    assert isinstance(catalog, dict)
    assert catalog["public_workflow_commands"] == 9
    assert catalog["adapter_ops_commands"] == 5
    public_ids = {
        command["id"]
        for command in catalog["commands"]
        if command["namespace"] == "workflow"
        and command["category"] in {"lifecycle", "macro"}
    }
    assert public_ids == {
        "route-next",
        "research-brief",
        "idea-to-prd",
        "implementation-kickoff",
        "team-sync",
        "integration-plan",
        "review-gate",
        "release-readiness",
        "company-run",
    }


def test_show_command_tool_payload_supports_company_run(tmp_path: Path) -> None:
    payload = show_command_tool_payload(cwd=tmp_path, command_id="builtin:company-run")

    assert payload["ok"] is True
    assert payload["command_id"] == "company-run"
    assert payload["qualified_id"] == "builtin:company-run"
    recipe = payload["recipe"]
    assert isinstance(recipe, dict)
    assert recipe["category"] == "macro"


def test_preview_command_tool_payload_injects_objective(tmp_path: Path) -> None:
    payload = preview_command_tool_payload(
        cwd=tmp_path,
        command_id="builtin:research-brief",
        objective="Find the safest MCP shape for omx-agent commands.",
    )

    assert payload["ok"] is True
    assert payload["command_id"] == "research-brief"
    plan = payload["plan"]
    assert isinstance(plan, dict)
    first_step = plan["steps"][0]
    assert first_step["codex_search"] is True
    assert "MCP tool-supplied context" in first_step["inline_prompt"]
    assert "safest MCP shape" in first_step["inline_prompt"]


def test_preview_command_tool_payload_shell_quotes_manual_commands(
    tmp_path: Path,
) -> None:
    payload = preview_command_tool_payload(
        cwd=tmp_path,
        command_id="builtin:research-brief",
        objective="audit; echo PWNED\nwith spaces",
    )

    manual_commands = payload["manual_commands"]
    assert isinstance(manual_commands, list)
    plan = payload["plan"]
    assert isinstance(plan, dict)
    steps = plan["steps"]
    assert isinstance(steps, list)
    first_step = steps[0]
    assert isinstance(first_step, dict)
    native_argv = first_step["native_argv"]
    assert isinstance(native_argv, list)

    command_text = manual_commands[0]
    assert shlex.split(command_text) == native_argv
    assert "audit; echo PWNED" in command_text
    assert "\nwith spaces" in command_text
    assert " --search " in command_text


def test_preview_company_run_returns_dry_run_macro_plan(tmp_path: Path) -> None:
    payload = preview_command_tool_payload(
        cwd=tmp_path,
        command_id="builtin:company-run",
        objective="Build a company-style agent workflow.",
    )

    assert payload["ok"] is True
    assert payload["command_id"] == "company-run"
    plan = payload["plan"]
    assert isinstance(plan, dict)
    assert plan["risk"] == "launches_runtime"
    assert plan["dry_run"] is True
    plan_text = orjson.dumps(plan).decode()
    assert "research-vote.md" in plan_text
    assert "proceed-vote.md" in plan_text
    assert "alexandria_mcp" in plan_text
    assert "omx_team" in plan_text


def test_unknown_command_preview_returns_missing_command_error(tmp_path: Path) -> None:
    with pytest.raises(CommandCatalogResolutionError, match="No command named"):
        preview_command_tool_payload(
            cwd=tmp_path,
            command_id="builtin:not-a-command",
            objective="unknown name",
        )


def test_omx_agent_mcp_server_advertises_canonical_workflow_tools() -> None:
    async def run_check() -> list[str]:
        server = build_omx_agent_mcp_server(cwd=".")
        tools = await server.list_tools()
        names = [tool.name for tool in tools]
        return names

    tool_names = asyncio.run(run_check())

    assert "omx_agent_preview_command" in tool_names
    assert "research_brief" in tool_names
    assert "idea_to_prd" in tool_names
    assert "release_readiness" in tool_names
    assert "company_run" in tool_names


def test_omx_agent_mcp_server_tool_call_returns_typed_company_plan(
    tmp_path: Path,
) -> None:
    async def run_call() -> dict[str, object]:
        server = build_omx_agent_mcp_server(cwd=tmp_path)
        result = await server.call_tool(
            "company_run",
            {"objective": "Design an agent-friendly company loop."},
        )
        payload = _text_payload(result)
        return payload

    payload = asyncio.run(run_call())

    assert payload["ok"] is True
    assert payload["qualified_id"] == "builtin:company-run"
    plan = payload["plan"]
    assert isinstance(plan, dict)
    assert plan["risk"] == "launches_runtime"
    first_step = plan["steps"][0]
    assert "agent-friendly company loop" in first_step["inline_prompt"]
    assert payload["warnings"] == [
        "MCP tool returns a dry-run plan only; it does not execute native Codex/OMX commands."
    ]
