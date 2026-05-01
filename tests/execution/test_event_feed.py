from execution.event_feed import decode_event_lines


def test_decode_event_lines_ignores_non_json_lines() -> None:
    payload = 'note\n{"type": "turn.started"}\n'

    events = decode_event_lines(payload)

    assert events == [{"type": "turn.started"}]


def test_decode_event_lines_keeps_transport_parse_separate_from_contracts() -> None:
    payload = '{"type": "turn.started", "extra": {"debug": true}}\n'

    events = decode_event_lines(payload)

    assert events == [{"type": "turn.started", "extra": {"debug": True}}]
