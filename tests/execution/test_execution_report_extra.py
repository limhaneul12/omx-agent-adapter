import pytest

from omx_remote.execution.payload_mapping import build_tool_interaction_report, promote_execution_contract


def test_build_tool_interaction_report_preserves_anomaly_category_order() -> None:
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
                "arguments": '{"expression":"s/a/b/"}',
        }
    )
    matched_result = promote_execution_contract(
        {
            "type": "tool_result",
            "tool_name": "sed",
            "call_id": "call-456",
            "text": "ok",
        }
    )
    duplicate_result = promote_execution_contract(
        {
            "type": "tool_result",
            "tool_name": "sed",
            "call_id": "call-456",
            "text": "duplicate",
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

    assert [anomaly.category for anomaly in report.anomalies] == [
        "duplicate_result",
        "unmatched_result",
        "missing_result",
    ]


def test_build_tool_interaction_report_preserves_duplicate_result_input_order() -> None:
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
            "text": "first",
        }
    )
    second_result = promote_execution_contract(
        {
            "type": "tool_result",
            "tool_name": "grep",
            "call_id": "call-123",
            "text": "second",
        }
    )
    third_result = promote_execution_contract(
        {
            "type": "tool_result",
            "tool_name": "grep",
            "call_id": "call-123",
            "text": "third",
        }
    )

    report = build_tool_interaction_report(
        [tool_call, first_result, second_result, third_result]
    )

    assert [result.text for result in report.duplicate_results] == ["second", "third"]


def test_build_tool_interaction_report_preserves_unmatched_result_input_order() -> None:
    first_orphan = promote_execution_contract(
        {
            "type": "tool_result",
            "tool_name": "awk",
            "call_id": "call-111",
            "text": "first-orphan",
        }
    )
    second_orphan = promote_execution_contract(
        {
            "type": "tool_result",
            "tool_name": "sed",
            "call_id": "call-222",
            "text": "second-orphan",
        }
    )

    report = build_tool_interaction_report([first_orphan, second_orphan])

    assert [result.text for result in report.unmatched_results] == [
        "first-orphan",
        "second-orphan",
    ]
