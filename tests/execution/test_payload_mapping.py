import pytest

from execution.payload_mapping import (
    build_tool_interaction,
    build_tool_interaction_report,
    build_tool_interactions,
    is_promotable_execution_payload,
    promote_exec_message,
    promote_exec_output,
    promote_exec_tool_call,
    promote_exec_tool_result,
    promote_execution_contract,
    route_execution_payload,
    split_event_payloads,
)
from shared.exceptions.execution_exceptions import UnsupportedExecutionPayloadError


def test_split_event_payloads_returns_payload_by_default() -> None:
    payload = {"type": "turn.started", "id": "t1"}

    result = split_event_payloads(payload)

    assert result == [payload]


def test_split_event_payloads_extracts_item_completed_item_payload() -> None:
    payload = {
        "type": "item.completed",
        "item": {"type": "message", "text": "done"},
    }

    result = split_event_payloads(payload)

    assert result == [{"type": "message", "text": "done"}]


def test_split_event_payloads_extracts_item_completed_output_item_payload() -> None:
    payload = {
        "type": "item.completed",
        "item": {"type": "output_text", "text": "stream line"},
    }

    result = split_event_payloads(payload)

    assert result == [{"type": "output_text", "text": "stream line"}]


def test_split_event_payloads_extracts_item_completed_tool_result_payload() -> None:
    payload = {
        "type": "item.completed",
        "item": {
            "type": "tool_result",
            "tool_name": "grep",
            "call_id": "call-123",
            "text": "match",
        },
    }

    result = split_event_payloads(payload)

    assert result == [
        {
            "type": "tool_result",
            "tool_name": "grep",
            "call_id": "call-123",
            "text": "match",
        }
    ]


def test_split_event_payloads_keeps_item_completed_payload_when_item_is_not_dict() -> None:
    payload = {"type": "item.completed", "item": ["not", "a", "mapping"]}

    result = split_event_payloads(payload)

    assert result == [payload]


def test_is_promotable_execution_payload_accepts_supported_type() -> None:
    payload = {"type": "message", "text": "done"}

    result = is_promotable_execution_payload(payload)

    assert result is True


def test_is_promotable_execution_payload_rejects_unsupported_type() -> None:
    payload = {"type": "turn.started", "id": "t1"}

    result = is_promotable_execution_payload(payload)

    assert result is False


def test_route_execution_payload_promotes_supported_payload_type() -> None:
    payload = {"type": "message", "text": "done"}

    result = route_execution_payload(payload)

    assert result.__class__.__name__ == "ExecMessage"
    assert result.kind == "message"
    assert result.text == "done"


def test_route_execution_payload_keeps_raw_passthrough_for_unsupported_type() -> None:
    payload = {"type": "turn.started", "id": "t1"}

    result = route_execution_payload(payload)

    assert result == payload


    payload = {
        "type": "item.completed",
        "item": {
            "type": "tool_result",
            "tool_name": "grep",
            "call_id": "call-123",
            "text": "match",
        },
    }

    result = split_event_payloads(payload)

    assert result == [
        {
            "type": "tool_result",
            "tool_name": "grep",
            "call_id": "call-123",
            "text": "match",
        }
    ]


def test_promote_exec_message_builds_contract_from_payload() -> None:
    payload = {"type": "message", "text": "done"}

    result = promote_exec_message(payload)

    assert result.kind == "message"
    assert result.text == "done"


def test_promote_exec_output_builds_contract_from_payload() -> None:
    payload = {"type": "output_text", "text": "stream line"}

    result = promote_exec_output(payload)

    assert result.kind == "output_text"
    assert result.text == "stream line"


def test_promote_exec_tool_result_builds_contract_from_payload() -> None:
    payload = {
        "type": "tool_result",
        "tool_name": "grep",
        "call_id": "call-123",
        "text": "match",
    }

    result = promote_exec_tool_result(payload)

    assert result.kind == "tool_result"
    assert result.tool_name == "grep"
    assert result.call_id == "call-123"
    assert result.text == "match"


def test_promote_exec_tool_call_builds_contract_from_payload() -> None:
    payload = {
        "type": "tool_call",
        "tool_name": "grep",
        "call_id": "call-123",
        "arguments": '{"pattern":"TODO"}',
    }

    result = promote_exec_tool_call(payload)

    assert result.kind == "tool_call"
    assert result.tool_name == "grep"
    assert result.call_id == "call-123"
    assert result.arguments == '{"pattern":"TODO"}'


def test_promote_execution_contract_selects_message_contract() -> None:
    payload = {"type": "message", "text": "done"}

    result = promote_execution_contract(payload)

    assert result.kind == "message"
    assert result.text == "done"
    assert result.__class__.__name__ == "ExecMessage"


def test_promote_execution_contract_selects_output_contract() -> None:
    payload = {"type": "output_text", "text": "stream line"}

    result = promote_execution_contract(payload)

    assert result.kind == "output_text"
    assert result.text == "stream line"
    assert result.__class__.__name__ == "ExecOutput"


def test_promote_execution_contract_selects_tool_result_contract() -> None:
    payload = {
        "type": "tool_result",
        "tool_name": "grep",
        "call_id": "call-123",
        "text": "match",
    }

    result = promote_execution_contract(payload)

    assert result.kind == "tool_result"
    assert result.tool_name == "grep"
    assert result.call_id == "call-123"
    assert result.text == "match"
    assert result.__class__.__name__ == "ExecToolResult"


def test_promote_execution_contract_selects_tool_call_contract() -> None:
    payload = {
        "type": "tool_call",
        "tool_name": "grep",
        "call_id": "call-123",
        "arguments": '{"pattern":"TODO"}',
    }

    result = promote_execution_contract(payload)

    assert result.kind == "tool_call"
    assert result.tool_name == "grep"
    assert result.call_id == "call-123"
    assert result.arguments == '{"pattern":"TODO"}'
    assert result.__class__.__name__ == "ExecToolCall"


def test_promote_execution_contract_selects_output_contract_for_item_completed_output() -> None:
    event_payload = {
        "type": "item.completed",
        "item": {"type": "output_text", "text": "stream line"},
    }

    split_payloads = split_event_payloads(event_payload)
    result = promote_execution_contract(split_payloads[0])

    assert result.kind == "output_text"
    assert result.text == "stream line"
    assert result.__class__.__name__ == "ExecOutput"


def test_promote_execution_contract_selects_message_contract_for_item_completed_message() -> None:
    event_payload = {
        "type": "item.completed",
        "item": {"type": "message", "text": "done"},
    }

    split_payloads = split_event_payloads(event_payload)
    result = promote_execution_contract(split_payloads[0])

    assert result.kind == "message"
    assert result.text == "done"
    assert result.__class__.__name__ == "ExecMessage"


def test_promote_execution_contract_selects_tool_result_contract_for_item_completed_tool_result() -> None:
    event_payload = {
        "type": "item.completed",
        "item": {
            "type": "tool_result",
            "tool_name": "grep",
            "call_id": "call-123",
            "text": "match",
        },
    }

    split_payloads = split_event_payloads(event_payload)
    result = promote_execution_contract(split_payloads[0])

    assert result.kind == "tool_result"
    assert result.tool_name == "grep"
    assert result.call_id == "call-123"
    assert result.text == "match"
    assert result.__class__.__name__ == "ExecToolResult"


def test_promote_execution_contract_selects_tool_result_contract_for_item_completed_tool_call() -> None:
    event_payload = {
        "type": "item.completed",
        "item": {
            "type": "tool_call",
            "tool_name": "grep",
            "call_id": "call-123",
            "arguments": '{"pattern":"TODO"}',
        },
    }

    split_payloads = split_event_payloads(event_payload)
    result = promote_execution_contract(split_payloads[0])

    assert result.kind == "tool_call"
    assert result.tool_name == "grep"
    assert result.call_id == "call-123"
    assert result.arguments == '{"pattern":"TODO"}'
    assert result.__class__.__name__ == "ExecToolCall"


def test_build_tool_interaction_returns_completed_state_for_matched_result() -> None:
    tool_call = promote_execution_contract(
        {
            "type": "tool_call",
            "tool_name": "grep",
            "call_id": "call-123",
            "arguments": '{"pattern":"TODO"}',
        }
    )
    tool_result = promote_execution_contract(
        {
            "type": "tool_result",
            "tool_name": "grep",
            "call_id": "call-123",
            "text": "match",
        }
    )

    result = build_tool_interaction([tool_call, tool_result])

    assert result.state == "completed"


def test_build_tool_interaction_returns_missing_result_state_without_match() -> None:
    tool_call = promote_execution_contract(
        {
            "type": "tool_call",
            "tool_name": "grep",
            "call_id": "call-123",
            "arguments": '{"pattern":"TODO"}',
        }
    )

    result = build_tool_interaction([tool_call])

    assert result.state == "missing_result"


def test_build_tool_interaction_returns_joined_tool_call_and_result() -> None:
    tool_call = promote_execution_contract(
        {
            "type": "tool_call",
            "tool_name": "grep",
            "call_id": "call-123",
            "arguments": '{"pattern":"TODO"}',
        }
    )
    tool_result = promote_execution_contract(
        {
            "type": "tool_result",
            "tool_name": "grep",
            "call_id": "call-123",
            "text": "match",
        }
    )

    result = build_tool_interaction([tool_call, tool_result])

    assert result.call.call_id == "call-123"
    assert result.state == "completed"
    assert result.call.tool_name == "grep"
    assert result.call.arguments == '{"pattern":"TODO"}'
    assert result.state == "completed"
    assert result.result is not None
    assert result.result.call_id == "call-123"
    assert result.result.text == "match"


def test_build_tool_interaction_keeps_call_without_result() -> None:
    tool_call = promote_execution_contract(
        {
            "type": "tool_call",
            "tool_name": "grep",
            "call_id": "call-123",
            "arguments": '{"pattern":"TODO"}',
        }
    )

    result = build_tool_interaction([tool_call])

    assert result.call.call_id == "call-123"
    assert result.state == "missing_result"
    assert result.result is None


def test_build_tool_interactions_groups_multiple_call_id_matched_pairs() -> None:
    first_call = promote_execution_contract(
        {
            "type": "tool_call",
            "tool_name": "grep",
            "call_id": "call-123",
            "arguments": '{"pattern":"TODO"}',
        }
    )
    second_call = promote_execution_contract(
        {
            "type": "tool_call",
            "tool_name": "sed",
            "call_id": "call-456",
            "arguments": '{"script":"s/x/y/"}',
        }
    )
    second_result = promote_execution_contract(
        {
            "type": "tool_result",
            "tool_name": "sed",
            "call_id": "call-456",
            "text": "updated",
        }
    )
    first_result = promote_execution_contract(
        {
            "type": "tool_result",
            "tool_name": "grep",
            "call_id": "call-123",
            "text": "match",
        }
    )

    result = build_tool_interactions(
        [first_call, second_call, second_result, first_result]
    )

    assert len(result) == 2
    assert result[0].call.call_id == "call-123"
    assert result[0].result is not None
    assert result[0].result.call_id == "call-123"
    assert result[1].call.call_id == "call-456"
    assert result[1].result is not None
    assert result[1].result.call_id == "call-456"


def test_build_tool_interaction_ignores_result_with_different_call_id() -> None:
    tool_call = promote_execution_contract(
        {
            "type": "tool_call",
            "tool_name": "grep",
            "call_id": "call-123",
            "arguments": '{"pattern":"TODO"}',
        }
    )
    tool_result = promote_execution_contract(
        {
            "type": "tool_result",
            "tool_name": "grep",
            "call_id": "call-999",
            "text": "other-match",
        }
    )

    result = build_tool_interaction([tool_call, tool_result])

    assert result.call.call_id == "call-123"
    assert result.result is None


def test_build_tool_interaction_uses_first_matching_result_for_duplicate_call_id() -> None:
    tool_call = promote_execution_contract(
        {
            "type": "tool_call",
            "tool_name": "grep",
            "call_id": "call-123",
            "arguments": '{"pattern":"TODO"}',
        }
    )
    first_result = promote_execution_contract(
        {
            "type": "tool_result",
            "tool_name": "grep",
            "call_id": "call-123",
            "text": "first-match",
        }
    )
    second_result = promote_execution_contract(
        {
            "type": "tool_result",
            "tool_name": "grep",
            "call_id": "call-123",
            "text": "second-match",
        }
    )

    result = build_tool_interaction([tool_call, first_result, second_result])

    assert result.result is not None
    assert result.result.text == "first-match"


def test_build_tool_interaction_report_surfaces_unmatched_tool_result() -> None:
    tool_call = promote_execution_contract(
        {
            "type": "tool_call",
            "tool_name": "grep",
            "call_id": "call-123",
            "arguments": '{"pattern":"TODO"}',
        }
    )
    unmatched_result = promote_execution_contract(
        {
            "type": "tool_result",
            "tool_name": "grep",
            "call_id": "call-999",
            "text": "orphan-match",
        }
    )

    report = build_tool_interaction_report([tool_call, unmatched_result])

    assert len(report.interactions) == 1
    assert report.interactions[0].call.call_id == "call-123"
    assert report.interactions[0].state == "missing_result"
    assert report.interactions[0].result is None
    assert len(report.unmatched_results) == 1
    assert report.unmatched_results[0].call_id == "call-999"
    assert report.unmatched_results[0].text == "orphan-match"
    assert report.anomalies[0].summary == "tool result did not match any known tool call"


def test_build_tool_interaction_report_surfaces_same_text_duplicate_result() -> None:
    tool_call = promote_execution_contract(
        {
            "type": "tool_call",
            "tool_name": "grep",
            "call_id": "call-123",
            "arguments": '{"pattern":"TODO"}',
        }
    )
    first_result = promote_execution_contract(
        {
            "type": "tool_result",
            "tool_name": "grep",
            "call_id": "call-123",
            "text": "match",
        }
    )
    duplicate_result = promote_execution_contract(
        {
            "type": "tool_result",
            "tool_name": "grep",
            "call_id": "call-123",
            "text": "match",
        }
    )

    report = build_tool_interaction_report(
        [tool_call, first_result, duplicate_result]
    )

    assert len(report.interactions) == 1
    assert report.interactions[0].result is not None
    assert report.interactions[0].result.text == "match"
    assert len(report.duplicate_results) == 1
    assert report.duplicate_results[0].call_id == "call-123"
    assert report.duplicate_results[0].text == "match"
    assert report.anomalies[0].category == "duplicate_result"


def test_build_tool_interaction_report_surfaces_duplicate_results_separately() -> None:
    tool_call = promote_execution_contract(
        {
            "type": "tool_call",
            "tool_name": "grep",
            "call_id": "call-123",
            "arguments": '{"pattern":"TODO"}',
        }
    )
    first_result = promote_execution_contract(
        {
            "type": "tool_result",
            "tool_name": "grep",
            "call_id": "call-123",
            "text": "first-match",
        }
    )
    duplicate_result = promote_execution_contract(
        {
            "type": "tool_result",
            "tool_name": "grep",
            "call_id": "call-123",
            "text": "duplicate-match",
        }
    )

    report = build_tool_interaction_report(
        [tool_call, first_result, duplicate_result]
    )

    assert len(report.interactions) == 1
    assert report.interactions[0].state == "completed"
    assert report.interactions[0].result is not None
    assert report.interactions[0].result.text == "first-match"
    assert len(report.unmatched_results) == 0
    assert len(report.duplicate_results) == 1
    assert report.duplicate_results[0].call_id == "call-123"
    assert report.duplicate_results[0].text == "duplicate-match"
    assert report.anomalies[0].summary == "additional tool result observed after first matched result"


def test_build_tool_interaction_report_separates_orphan_and_duplicate_results() -> None:
    tool_call = promote_execution_contract(
        {
            "type": "tool_call",
            "tool_name": "grep",
            "call_id": "call-123",
            "arguments": '{"pattern":"TODO"}',
        }
    )
    matched_result = promote_execution_contract(
        {
            "type": "tool_result",
            "tool_name": "grep",
            "call_id": "call-123",
            "text": "first-match",
        }
    )
    duplicate_result = promote_execution_contract(
        {
            "type": "tool_result",
            "tool_name": "grep",
            "call_id": "call-123",
            "text": "duplicate-match",
        }
    )
    orphan_result = promote_execution_contract(
        {
            "type": "tool_result",
            "tool_name": "sed",
            "call_id": "call-999",
            "text": "orphan-match",
        }
    )

    report = build_tool_interaction_report(
        [tool_call, matched_result, duplicate_result, orphan_result]
    )

    assert len(report.unmatched_results) == 1
    assert report.unmatched_results[0].call_id == "call-999"
    assert report.unmatched_results[0].text == "orphan-match"
    assert len(report.duplicate_results) == 1
    assert report.duplicate_results[0].call_id == "call-123"
    assert report.duplicate_results[0].text == "duplicate-match"


def test_build_tool_interaction_report_surfaces_missing_result_calls() -> None:
    missing_result_call = promote_execution_contract(
        {
            "type": "tool_call",
            "tool_name": "grep",
            "call_id": "call-123",
            "arguments": '{"pattern":"TODO"}',
        }
    )
    matched_call = promote_execution_contract(
        {
            "type": "tool_call",
            "tool_name": "sed",
            "call_id": "call-456",
            "arguments": '{"script":"s/x/y/"}',
        }
    )
    matched_result = promote_execution_contract(
        {
            "type": "tool_result",
            "tool_name": "sed",
            "call_id": "call-456",
            "text": "updated",
        }
    )

    report = build_tool_interaction_report(
        [missing_result_call, matched_call, matched_result]
    )

    assert len(report.interactions) == 2
    assert report.interactions[0].state == "missing_result"
    assert report.interactions[1].state == "completed"
    assert len(report.missing_result_calls) == 1
    assert report.missing_result_calls[0].call_id == "call-123"
    assert report.anomalies[-1].summary == "tool call completed without a matching tool result"
    assert report.missing_result_calls[0].tool_name == "grep"


def test_build_tool_interaction_report_builds_structured_anomalies() -> None:
    missing_result_call = promote_execution_contract(
        {
            "type": "tool_call",
            "tool_name": "grep",
            "call_id": "call-123",
            "arguments": '{"pattern":"TODO"}',
        }
    )
    matched_call = promote_execution_contract(
        {
            "type": "tool_call",
            "tool_name": "sed",
            "call_id": "call-456",
            "arguments": '{"script":"s/x/y/"}',
        }
    )
    matched_result = promote_execution_contract(
        {
            "type": "tool_result",
            "tool_name": "sed",
            "call_id": "call-456",
            "text": "updated",
        }
    )
    duplicate_result = promote_execution_contract(
        {
            "type": "tool_result",
            "tool_name": "sed",
            "call_id": "call-456",
            "text": "duplicate-updated",
        }
    )
    orphan_result = promote_execution_contract(
        {
            "type": "tool_result",
            "tool_name": "awk",
            "call_id": "call-999",
            "text": "orphan",
        }
    )

    report = build_tool_interaction_report(
        [
            missing_result_call,
            matched_call,
            matched_result,
            duplicate_result,
            orphan_result,
        ]
    )

    assert len(report.anomalies) == 3
    assert report.anomalies[0].category == "duplicate_result"
    assert report.anomalies[0].related_call_id == "call-456"
    assert report.anomalies[0].tool_name == "sed"
    assert report.anomalies[1].category == "unmatched_result"
    assert report.anomalies[1].related_call_id == "call-999"
    assert report.anomalies[1].tool_name == "awk"
    assert report.anomalies[2].category == "missing_result"
    assert report.anomalies[2].related_call_id == "call-123"
    assert report.anomalies[2].tool_name == "grep"


def test_promote_execution_contract_rejects_unsupported_payload_type() -> None:
    payload = {"type": "turn.started", "id": "t1"}

    with pytest.raises(
        UnsupportedExecutionPayloadError,
        match=r"unsupported execution payload type: turn\.started",
    ):
        promote_execution_contract(payload)
