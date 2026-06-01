import pytest
from pydantic import ValidationError

from omx_remote.adapter_types.type_contract.execution_contract_type import (
    KNOWN_EXECUTION_EVENT_TYPES,
    PROMOTABLE_EXECUTION_PAYLOAD_TYPES,
)
from omx_remote.schemas.execution.event_schemas import (
    ExecCommandExecution,
    ExecMessage,
    ExecToolCall,
    ExecToolResult,
    TurnUsage,
)
from omx_remote.schemas.execution.interaction_schemas import (
    ToolInteraction,
    ToolInteractionAnomaly,
    ToolInteractionReport,
)
from omx_remote.schemas.execution.request_schemas import (
    ExecRequest,
    ExecutionEventDecodeRequest,
)
from omx_remote.shared.omx_enums.execution_enums import (
    ExecutionPayloadKind,
    KnownExecutionEventType,
    PromotableExecutionPayloadType,
)


def test_known_execution_event_type_enum_values_and_docstring() -> None:
    assert KnownExecutionEventType.__doc__
    assert KnownExecutionEventType.THREAD_STARTED == "thread.started"
    assert KnownExecutionEventType.TURN_STARTED == "turn.started"
    assert KnownExecutionEventType.ITEM_COMPLETED == "item.completed"
    assert KnownExecutionEventType.TURN_COMPLETED == "turn.completed"


def test_promotable_execution_payload_type_enum_values_and_docstring() -> None:
    assert PromotableExecutionPayloadType.__doc__
    assert PromotableExecutionPayloadType.MESSAGE == "message"
    assert PromotableExecutionPayloadType.OUTPUT_TEXT == "output_text"
    assert PromotableExecutionPayloadType.COMMAND_EXECUTION == "command_execution"
    assert PromotableExecutionPayloadType.TOOL_CALL == "tool_call"
    assert PromotableExecutionPayloadType.TOOL_RESULT == "tool_result"


def test_execution_marker_sets_are_enum_backed() -> None:
    assert frozenset(KnownExecutionEventType) == KNOWN_EXECUTION_EVENT_TYPES
    assert (
        frozenset(PromotableExecutionPayloadType) == PROMOTABLE_EXECUTION_PAYLOAD_TYPES
    )
    assert all(
        isinstance(event_type, KnownExecutionEventType)
        for event_type in KNOWN_EXECUTION_EVENT_TYPES
    )
    assert all(
        isinstance(payload_type, PromotableExecutionPayloadType)
        for payload_type in PROMOTABLE_EXECUTION_PAYLOAD_TYPES
    )


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

    assert result.kind == ExecutionPayloadKind.MESSAGE.value


def test_exec_command_execution_uses_named_execution_payload_kind() -> None:
    result = ExecCommandExecution.model_validate(
        {
            "kind": "command_execution",
            "command": "/bin/zsh -lc pwd",
            "aggregated_output": "/tmp\n",
            "exit_code": 0,
            "status": "completed",
        }
    )

    assert result.kind == ExecutionPayloadKind.COMMAND_EXECUTION.value
    assert result.command == "/bin/zsh -lc pwd"
    assert result.aggregated_output == "/tmp\n"
    assert result.exit_code == 0
    assert result.status == "completed"


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


def test_tool_interaction_rejects_missing_result_state_when_result_is_present() -> None:
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
                "has_anomalies": False,
                "anomaly_count": 0,
                "unexpected": True,
            }
        )


def test_tool_interaction_report_coerces_collection_fields_to_tuples() -> None:
    result = ToolInteractionReport.model_validate(
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
            "has_anomalies": False,
            "anomaly_count": 0,
        }
    )

    assert result.interactions == ()
    assert result.unmatched_results == ()
    assert result.duplicate_results == ()
    assert result.missing_result_calls == ()
    assert result.anomalies == ()


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
                "interaction_count": 1,
                "completed_count": 1,
                "missing_result_count": 0,
                "duplicate_result_count": 0,
                "unmatched_result_count": 0,
                "has_anomalies": False,
                "anomaly_count": 1,
            }
        )


def test_turn_usage_accepts_stable_token_counters() -> None:
    result = TurnUsage.model_validate(
        {
            "input_tokens": 21847,
            "cached_input_tokens": 7552,
            "output_tokens": 16,
            "reasoning_output_tokens": 9,
        }
    )

    assert result.input_tokens == 21847
    assert result.cached_input_tokens == 7552
    assert result.output_tokens == 16
    assert result.reasoning_output_tokens == 9


def test_turn_usage_rejects_negative_token_counters() -> None:
    with pytest.raises(ValidationError):
        TurnUsage.model_validate(
            {
                "input_tokens": -1,
                "cached_input_tokens": 0,
                "output_tokens": 16,
                "reasoning_output_tokens": 9,
            }
        )


def test_turn_usage_rejects_unexpected_extra_fields() -> None:
    with pytest.raises(ValidationError):
        TurnUsage.model_validate(
            {
                "input_tokens": 1,
                "cached_input_tokens": 0,
                "output_tokens": 1,
                "reasoning_output_tokens": 0,
                "unexpected": True,
            }
        )
