from execution.payload_mapping import promote_exec_message, split_event_payloads


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


def test_promote_exec_message_builds_contract_from_payload() -> None:
    payload = {"type": "message", "text": "done"}

    result = promote_exec_message(payload)

    assert result.kind == "message"
    assert result.text == "done"
