import asyncio
import inspect
import json

from omx_remote.execution.event_feed import decode_event_lines
from omx_remote.schemas.execution.request_schemas import ExecutionEventDecodeRequest


def test_decode_event_lines_ignores_non_json_lines() -> None:
    payload = 'note\n{"type": "turn.started"}\n'

    events = asyncio.run(decode_event_lines(payload))

    assert len(events) == 1
    assert events[0]["type"] == "turn.started"


def test_decode_event_lines_accepts_typed_request() -> None:
    request = ExecutionEventDecodeRequest(
        payload='note\n{"type": "turn.started"}\n'
    )

    events = asyncio.run(decode_event_lines(request))

    assert len(events) == 1
    assert events[0]["type"] == "turn.started"


def test_decode_event_lines_keeps_transport_parse_separate_from_contracts() -> None:
    payload = '{"type": "turn.started", "extra": {"debug": true}}\n'

    events = asyncio.run(decode_event_lines(payload))

    assert len(events) == 1
    assert events[0]["type"] == "turn.started"
    assert events[0]["extra"] == {"debug": True}


def test_decode_event_lines_splits_item_completed_payloads() -> None:
    payload = '{"type":"item.completed","item":{"type":"tool_result","tool_name":"grep","call_id":"call-123","text":"match"}}\n'

    events = asyncio.run(decode_event_lines(payload))

    assert len(events) == 1
    assert events[0]["type"] == "tool_result"
    assert events[0]["tool_name"] == "grep"
    assert events[0]["call_id"] == "call-123"
    assert events[0]["text"] == "match"


def test_decode_event_lines_keeps_item_completed_wrapper_for_unsupported_item_payload() -> (
    None
):
    payload = '{"type":"item.completed","item":{"type":"turn.started","id":"t1"}}\n'

    events = asyncio.run(decode_event_lines(payload))

    assert len(events) == 1
    assert events[0]["type"] == "item.completed"
    assert events[0]["item"] == {"type": "turn.started", "id": "t1"}


def test_decode_event_lines_skips_malformed_json_without_dropping_valid_neighbors() -> (
    None
):
    payload = "\n".join(
        [
            '{"type":"turn.started","id":"before"}',
            '{"type":"broken",',
            '{"type":"turn.completed","id":"after"}',
        ]
    )

    events = asyncio.run(decode_event_lines(payload))

    assert len(events) == 2
    assert events[0]["type"] == "turn.started"
    assert events[0]["id"] == "before"
    assert events[1]["type"] == "turn.completed"
    assert events[1]["id"] == "after"


def test_decode_event_lines_is_async() -> None:
    assert inspect.iscoroutinefunction(decode_event_lines)


def test_decode_event_lines_skips_non_dict_json_payloads_without_dropping_valid_neighbors() -> (
    None
):
    payload = "\n".join(
        [
            '{"type":"turn.started","id":"before"}',
            '["not","a","mapping"]',
            '{"type":"turn.completed","id":"after"}',
        ]
    )

    events = asyncio.run(decode_event_lines(payload))

    assert len(events) == 2
    assert events[0]["type"] == "turn.started"
    assert events[0]["id"] == "before"
    assert events[1]["type"] == "turn.completed"
    assert events[1]["id"] == "after"


def test_decode_event_lines_splits_item_completed_command_execution_payloads() -> None:
    payload = (
        "\n".join(
            [
                "{\"type\":\"item.completed\",\"item\":{\"type\":\"command_execution\",\"command\":\"/bin/zsh -lc pwd\",\"aggregated_output\":\"/tmp\\n\",\"exit_code\":0,\"status\":\"completed\"}}",
                "{\"type\":\"turn.completed\",\"id\":\"after\"}",
            ]
        )
        + "\n"
    )

    events = asyncio.run(decode_event_lines(payload))

    assert len(events) == 2
    assert events[0]["type"] == "command_execution"
    assert events[0]["command"] == "/bin/zsh -lc pwd"
    assert events[0]["aggregated_output"] == "/tmp\n"
    assert events[0]["exit_code"] == 0
    assert events[0]["status"] == "completed"
    assert events[1]["type"] == "turn.completed"


def test_decode_event_lines_splits_item_completed_tool_call_payloads() -> None:
    payload = json.dumps(
        {
            "type": "item.completed",
            "item": {
                "type": "tool_call",
                "tool_name": "grep",
                "call_id": "call-123",
                "arguments": '{"pattern":"TODO"}',
            },
        }
    ) + "\n"

    events = asyncio.run(decode_event_lines(payload))

    assert len(events) == 1
    assert events[0]["type"] == "tool_call"
    assert events[0]["tool_name"] == "grep"
    assert events[0]["call_id"] == "call-123"
    assert events[0]["arguments"] == '{"pattern":"TODO"}'
