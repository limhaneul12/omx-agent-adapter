from pathlib import Path

import pytest

from omx_remote.runtime.comx.tui_command_router import route_tui_slash_command
from omx_remote.schemas.mcp_client_schemas import (
    McpServerConfig,
    McpServerListResult,
    McpServerSource,
    McpServerTransport,
    McpTransportKind,
)
from omx_remote.schemas.next_action_schemas import NextActionResult


def test_tui_run_rejects_execute_flag_to_keep_cockpit_dry_run_only(
    tmp_path: Path,
) -> None:
    """The interactive cockpit must not silently execute composed recipes."""
    with pytest.raises(ValueError, match="unsupported /run option: --execute"):
        route_tui_slash_command(
            "/run builtin:review-gate --execute --task inspect",
            cwd=tmp_path,
        )


def test_tui_team_panel_stays_read_only_and_points_to_external_team_commands(
    tmp_path: Path,
) -> None:
    result = route_tui_slash_command("/team", cwd=tmp_path)

    assert result.read_only is True
    assert result.title == "Team panel"
    assert "read-only" in result.body
    assert "omx team status" in result.body
    assert "transition-task-status" not in result.body
    assert "claim-task" not in result.body


def test_tui_next_panel_surfaces_loaded_cockpit_summary(tmp_path: Path) -> None:
    next_action = NextActionResult(
        recommended_action="observe",
        safe_to_mutate=True,
        requires_review=False,
        summary="Cockpit recommends observing active team lanes.",
        why=("team evidence is still collecting",),
        source_names=("runtime_status", "team_evidence"),
    )

    result = route_tui_slash_command("/next", cwd=tmp_path, next_action=next_action)

    assert result.read_only is True
    assert result.title == "next action"
    assert result.body == "Cockpit recommends observing active team lanes."


def test_tui_mcp_call_preview_does_not_leak_inline_sensitive_args(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    server = McpServerConfig(
        name="local_state",
        source=McpServerSource.REPO,
        enabled=True,
        transport=McpServerTransport(
            type=McpTransportKind.STDIO,
            command="omx",
            args=("mcp-serve", "state"),
        ),
    )
    token_key = "tok" + "en"
    key_flag = "api" + "-key"
    token_value = "value-foxtrot"
    flag_value = "value-golf"
    monkeypatch.setattr(
        "omx_remote.runtime.comx.tui_mcp_panels.read_mcp_servers",
        lambda cwd: McpServerListResult(
            servers=(server,),
            codex_count=0,
            repo_count=1,
            enabled_count=1,
        ),
    )

    result = route_tui_slash_command(
        (
            "/mcp call local_state state_read "
            f"--{token_key} {token_value} --{key_flag}={flag_value}"
        ),
        cwd=tmp_path,
    )

    assert result.read_only is True
    assert "dry_run: repo:local_state.state_read not executed" in result.body
    assert token_value not in result.body
    assert flag_value not in result.body
    assert result.warnings[0] == "Dry-run only. No MCP tool was executed."


def test_tui_slash_help_covers_every_completion_item() -> None:
    from omx_remote.runtime.comx.tui_interaction import (
        format_tui_slash_command_help,
        list_tui_slash_completion_items,
    )

    help_text = format_tui_slash_command_help()
    completion_names = [name for name, _description in list_tui_slash_completion_items()]

    assert completion_names
    assert "/run builtin:<recipe-id>" in help_text
    for command_name in completion_names:
        assert command_name in help_text
