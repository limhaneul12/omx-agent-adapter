import asyncio

import orjson

from omx_remote.execution.payload_mapping import (
    ExecutionPayload,
    load_execution_payload,
    split_event_payloads,
)
from omx_remote.schemas.execution_schemas import ExecutionEventDecodeRequest


async def decode_event_lines(
    request: ExecutionEventDecodeRequest | str,
) -> list[ExecutionPayload]:
    """Decodes raw execution event lines into transport payloads.

    Args:
        request [ExecutionEventDecodeRequest | str]: Typed decode request or raw JSONL-like execution stream text.

    Returns:
        list[ExecutionPayload]: Parsed transport payloads after malformed-line skipping and item-completed splitting.
    """
    normalized_request: ExecutionEventDecodeRequest
    if isinstance(request, ExecutionEventDecodeRequest):
        normalized_request = request
    else:
        normalized_request = ExecutionEventDecodeRequest(payload=request)

    events: list[ExecutionPayload] = await asyncio.to_thread(
        _decode_event_lines_sync,
        normalized_request.payload,
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
        normalized_event_payload: ExecutionPayload = load_execution_payload(
            "decoded execution event payload",
            event_payload,
        )
        split_payloads: list[ExecutionPayload] = split_event_payloads(
            normalized_event_payload
        )
        events.extend(split_payloads)
    return events
