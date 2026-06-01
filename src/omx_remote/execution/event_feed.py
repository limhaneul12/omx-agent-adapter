import orjson

from omx_remote.adapter_types.execution_types import ExecutionPayload
from omx_remote.execution.async_boundary import run_blocking_call
from omx_remote.execution.contract_promotion import split_event_payloads
from omx_remote.execution.payload_transport import load_execution_payload
from omx_remote.schemas.execution.request_schemas import ExecutionEventDecodeRequest


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

    events: list[ExecutionPayload] = await run_blocking_call(
        _decode_event_lines_sync,
        normalized_request.payload,
    )
    return events


def _decode_event_lines_sync(payload: str) -> list[ExecutionPayload]:
    """Handles decode event lines sync.

    Args:
        payload [str]: Function argument.

    Returns:
        list[ExecutionPayload]: Function return value.
    """
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
            payload_name="decoded execution event payload",
            payload=event_payload,
        )
        split_payloads: list[ExecutionPayload] = split_event_payloads(
            payload=normalized_event_payload
        )
        events.extend(split_payloads)
    return events
