import pytest
from pydantic import ValidationError

from schemas.execution_schemas import (
    ExecMessage,
    ExecRequest,
    ExecToolCall,
    ExecutionEventDecodeRequest,
)
from shared.omx_enums.execution_enums import ExecutionPayloadKind


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
