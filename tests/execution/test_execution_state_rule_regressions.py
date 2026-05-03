import pytest

from execution.payload_mapping import build_tool_interaction
from schemas.execution_schemas import ExecToolCall, ExecToolResult


def test_build_tool_interaction_returns_completed_state_without_ternary_shortcuts() -> None:
    tool_call = ExecToolCall(
        kind="tool_call",
        tool_name="grep",
        call_id="call-1",
        arguments='{"pattern":"TODO"}',
    )
    tool_result = ExecToolResult(
        kind="tool_result",
        tool_name="grep",
        call_id="call-1",
        text="ok",
    )

    result = build_tool_interaction([tool_call, tool_result])

    assert result.state == "completed"


def test_build_tool_interaction_returns_missing_result_state_without_ternary_shortcuts() -> None:
    tool_call = ExecToolCall(
        kind="tool_call",
        tool_name="grep",
        call_id="call-1",
        arguments='{"pattern":"TODO"}',
    )

    result = build_tool_interaction([tool_call])

    assert result.state == "missing_result"
