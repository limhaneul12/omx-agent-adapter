import asyncio
import inspect

from execution.event_feed import decode_event_lines


def test_decode_event_lines_ignores_non_json_lines() -> None:
    payload = 'note\n{"type": "turn.started"}\n'

    events = asyncio.run(decode_event_lines(payload))

    assert events == [{"type": "turn.started"}]


def test_decode_event_lines_keeps_transport_parse_separate_from_contracts() -> None:
    payload = '{"type": "turn.started", "extra": {"debug": true}}\n'

    events = asyncio.run(decode_event_lines(payload))

    assert events == [{"type": "turn.started", "extra": {"debug": True}}]


def test_decode_event_lines_skips_malformed_json_without_dropping_valid_neighbors() -> None:
    payload = '\n'.join(
        [
            '{"type":"turn.started","id":"before"}',
            '{"type":"broken",',
            '{"type":"turn.completed","id":"after"}',
        ]
    )

    events = asyncio.run(decode_event_lines(payload))

    assert events == [
        {"type": "turn.started", "id": "before"},
        {"type": "turn.completed", "id": "after"},
    ]


def test_decode_event_lines_is_async() -> None:
    assert inspect.iscoroutinefunction(decode_event_lines)
