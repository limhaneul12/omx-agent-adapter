import pytest
from pydantic import ValidationError

from omx_remote.schemas.execution_schemas import (
    ExecMessage,
    ExecRequest,
    ExecToolCall,
    ExecToolResult,
    ExecutionEventDecodeRequest,
    ToolInteraction,
    ToolInteractionAnomaly,
    ToolInteractionReport,
)
from omx_remote.shared.omx_enums.execution_enums import ExecutionPayloadKind


def test_exec_request_accepts_prompt_and_optional_cwd() -> None:
    result = ExecRequest.model_validate({"prompt": "ship it", "cwd": "/tmp"})

    assert result.prompt == "ship it"
    assert result.cwd == "/tmp"


def test_exec_request_rejects_unexpected_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ExecRequest.model_validate({"prompt": "ship it", "unexpected": True})


def test_exec_request_rejects_empty_cwd_when_present() -> None:
    with pytest.raises(ValidationError):
        ExecRequest.model_validate({"prompt": "ship it", "cwd": ""})


def test_execution_event_decode_request_accepts_non_empty_payload() -> None:
    result = ExecutionEventDecodeRequest.model_validate(
        {"payload": '{"type":"message","text":"done"}\n'}
    )

    assert result.payload == '{"type":"message","text":"done"}\n'


def test_execution_event_decode_request_rejects_empty_payload() -> None:
    with pytest.raises(ValidationError):
        ExecutionEventDecodeRequest.model_validate({"payload": ""})


def test_execution_event_decode_request_rejects_unexpected_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ExecutionEventDecodeRequest.model_validate(
            {
                "payload": '{"type":"message","text":"done"}\n',
                "unexpected": True,
            }
        )


def test_exec_message_uses_named_execution_payload_kind() -> None:
    result = ExecMessage.model_validate({"kind": "message", "text": "done"})

    assert result.kind is ExecutionPayloadKind.MESSAGE


def test_exec_tool_call_rejects_non_tool_call_kind() -> None:
    with pytest.raises(ValidationError):
        ExecToolCall.model_validate(
            {
                "kind": "message",
                "tool_name": "grep",
                "call_id": "call-123",
                "arguments": "{}",
            }
        )


def test_tool_interaction_rejects_completed_state_without_result() -> None:
    tool_call = ExecToolCall.model_validate(
        {
            "kind": "tool_call",
            "tool_name": "grep",
            "call_id": "call-123",
            "arguments": "{}",
        }
    )

    with pytest.raises(ValidationError):
        ToolInteraction.model_validate(
            {
                "state": "completed",
                "call": tool_call.model_dump(),
                "result": None,
            }
        )


def test_tool_interaction_rejects_missing_result_state_when_result_is_present() -> (
    None
):
    tool_call = ExecToolCall.model_validate(
        {
            "kind": "tool_call",
            "tool_name": "grep",
            "call_id": "call-123",
            "arguments": "{}",
        }
    )
    tool_result = ExecToolResult.model_validate(
        {
            "kind": "tool_result",
            "tool_name": "grep",
            "call_id": "call-123",
            "text": "match",
        }
    )

    with pytest.raises(ValidationError):
        ToolInteraction.model_validate(
            {
                "state": "missing_result",
                "call": tool_call.model_dump(),
                "result": tool_result.model_dump(),
            }
        )


def test_tool_interaction_rejects_result_for_different_call_id() -> None:
    tool_call = ExecToolCall.model_validate(
        {
            "kind": "tool_call",
            "tool_name": "grep",
            "call_id": "call-123",
            "arguments": "{}",
        }
    )
    tool_result = ExecToolResult.model_validate(
        {
            "kind": "tool_result",
            "tool_name": "grep",
            "call_id": "call-999",
            "text": "match",
        }
    )

    with pytest.raises(ValidationError):
        ToolInteraction.model_validate(
            {
                "state": "completed",
                "call": tool_call.model_dump(),
                "result": tool_result.model_dump(),
            }
        )


def test_tool_interaction_rejects_result_for_different_tool_name() -> None:
    tool_call = ExecToolCall.model_validate(
        {
            "kind": "tool_call",
            "tool_name": "grep",
            "call_id": "call-123",
            "arguments": "{}",
        }
    )
    tool_result = ExecToolResult.model_validate(
        {
            "kind": "tool_result",
            "tool_name": "sed",
            "call_id": "call-123",
            "text": "match",
        }
    )

    with pytest.raises(ValidationError):
        ToolInteraction.model_validate(
            {
                "state": "completed",
                "call": tool_call.model_dump(),
                "result": tool_result.model_dump(),
            }
        )


def test_tool_interaction_report_rejects_unexpected_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ToolInteractionReport.model_validate(
            {
                "interactions": [],
                "unmatched_results": [],
                "duplicate_results": [],
                "missing_result_calls": [],
                "anomalies": [],
                "interaction_count": 0,
                "completed_count": 0,
                "missing_result_count": 0,
                "duplicate_result_count": 0,
                "unmatched_result_count": 0,
                "unexpected": True,
            }
        )


def test_tool_interaction_report_rejects_inconsistent_summary_counts() -> None:
    tool_call = ExecToolCall.model_validate(
        {
            "kind": "tool_call",
            "tool_name": "grep",
            "call_id": "call-123",
            "arguments": "{}",
        }
    )
    tool_result = ExecToolResult.model_validate(
        {
            "kind": "tool_result",
            "tool_name": "grep",
            "call_id": "call-123",
            "text": "match",
        }
    )
    interaction = ToolInteraction.model_validate(
        {
            "state": "completed",
            "call": tool_call.model_dump(),
            "result": tool_result.model_dump(),
        }
    )
    anomaly = ToolInteractionAnomaly.model_validate(
        {
            "category": "duplicate_result",
            "related_call_id": "call-123",
            "tool_name": "grep",
            "summary": "duplicate tool result observed",
        }
    )

    with pytest.raises(ValidationError):
        ToolInteractionReport.model_validate(
            {
                "interactions": [interaction.model_dump()],
                "unmatched_results": [],
                "duplicate_results": [],
                "missing_result_calls": [],
                "anomalies": [anomaly.model_dump()],
                "interaction_count": 0,
                "completed_count": 0,
                "missing_result_count": 0,
                "duplicate_result_count": 0,
                "unmatched_result_count": 0,
            }
        )
