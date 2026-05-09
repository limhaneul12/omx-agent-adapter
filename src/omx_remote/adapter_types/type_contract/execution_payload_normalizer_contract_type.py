from collections.abc import Callable
from typing import cast

from omx_remote.adapter_types.execution_types import (
    ExecutionItemTransportPayload,
    ExecutionTransportPayload,
    ExecutionUsageTransportPayload,
)
from omx_remote.shared.omx_enums.execution_enums import ExecutionEventKind

type ExecutionEventPayloadNormalizer = Callable[
    [ExecutionTransportPayload], ExecutionTransportPayload
]


def _merge_thread_started_payload(
    payload: ExecutionTransportPayload,
) -> ExecutionTransportPayload:
    """Builds the normalized thread-started execution payload subset.

    Args:
        payload [ExecutionTransportPayload]: Execution transport payload carrying an optional thread id.

    Returns:
        ExecutionTransportPayload: Payload containing the normalized thread id field.
    """
    thread_id_value: object | None = payload.get("thread_id")
    normalized_thread_id: str = ""
    if isinstance(thread_id_value, str):
        normalized_thread_id = thread_id_value

    result = ExecutionTransportPayload(thread_id=normalized_thread_id)
    return result


def _merge_turn_completed_payload(
    payload: ExecutionTransportPayload,
) -> ExecutionTransportPayload:
    """Builds the normalized turn-completed execution payload subset.

    Args:
        payload [ExecutionTransportPayload]: Execution transport payload carrying optional usage counters.

    Returns:
        ExecutionTransportPayload: Payload containing the normalized usage field.
    """
    usage_value: object | None = payload.get("usage")
    usage_payload = ExecutionUsageTransportPayload()
    if isinstance(usage_value, dict):
        usage_payload = cast(ExecutionUsageTransportPayload, usage_value)

    result = ExecutionTransportPayload(usage=usage_payload)
    return result


def _merge_item_completed_payload(
    payload: ExecutionTransportPayload,
) -> ExecutionTransportPayload:
    """Builds the normalized item-completed execution payload subset.

    Args:
        payload [ExecutionTransportPayload]: Execution transport payload carrying an optional item object.

    Returns:
        ExecutionTransportPayload: Payload containing the normalized item field.
    """
    item_value: object | None = payload.get("item")
    item_payload = ExecutionItemTransportPayload()
    if isinstance(item_value, dict):
        item_payload = cast(ExecutionItemTransportPayload, item_value)

    result = ExecutionTransportPayload(item=item_payload)
    return result


EXECUTION_EVENT_PAYLOAD_NORMALIZERS: dict[
    ExecutionEventKind,
    ExecutionEventPayloadNormalizer,
] = {
    ExecutionEventKind.THREAD_STARTED: _merge_thread_started_payload,
    ExecutionEventKind.TURN_COMPLETED: _merge_turn_completed_payload,
    ExecutionEventKind.ITEM_COMPLETED: _merge_item_completed_payload,
}
