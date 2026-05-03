import pytest
from pydantic import ValidationError

from omx_remote.schemas.execution_schemas import ToolInteraction


def test_tool_interaction_accepts_completed_state_when_result_is_present() -> None:
    result = ToolInteraction.model_validate(
        {
            "state": "completed",
            "call": {
                "kind": "tool_call",
                "tool_name": "grep",
                "call_id": "call-123",
                "arguments": '{"pattern":"TODO"}',
            },
            "result": {
                "kind": "tool_result",
                "tool_name": "grep",
                "call_id": "call-123",
                "text": "match",
            },
        }
    )

    assert result.state == "completed"
    assert result.result is not None


def test_tool_interaction_rejects_completed_state_without_result() -> None:
    with pytest.raises(ValidationError):
        ToolInteraction.model_validate(
            {
                "state": "completed",
                "call": {
                    "kind": "tool_call",
                    "tool_name": "grep",
                    "call_id": "call-123",
                    "arguments": '{"pattern":"TODO"}',
                },
                "result": None,
            }
        )
