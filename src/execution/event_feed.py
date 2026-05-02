import asyncio

import orjson

from execution.payload_mapping import ExecutionPayload, split_event_payloads


async def decode_event_lines(payload: str) -> list[ExecutionPayload]:
    """Decodes raw execution event lines into transport payloads.

    Args:
        payload [str]: Raw JSONL-like execution stream text that will be parsed line by line.

    Returns:
        list[ExecutionPayload]: Parsed transport payloads after malformed-line skipping and item-completed splitting.
    """
    events: list[ExecutionPayload] = await asyncio.to_thread(
        _decode_event_lines_sync,
        payload,
    )
    return events


def _decode_event_lines_sync(payload: str) -> list[ExecutionPayload]:
    events: list[ExecutionPayload] = []
    line: str
    for line in payload.splitlines():
        normalized_line: str = line.strip()
        if not normalized_line or not normalized_line.startswith("{"):
            continue
        try:
            event_payload: object = orjson.loads(normalized_line)
        except orjson.JSONDecodeError:
            continue
        if not isinstance(event_payload, dict):
            continue
        split_payloads: list[ExecutionPayload] = split_event_payloads(event_payload)
        events.extend(split_payloads)
    return events
