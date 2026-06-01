from omx_remote.adapter_types.execution_types import (
    ExecutionPayload,
    ExecutionTransportPayload,
)
from omx_remote.execution.execution_payload_normalization import (
    _load_execution_transport_payload,
    _normalize_execution_event_payload,
    _normalize_execution_event_type,
    _normalize_execution_item_completed_payload,
    _normalize_execution_item_payload,
    _normalize_execution_thread_started_payload,
    _normalize_execution_turn_completed_payload,
    _normalize_execution_usage_payload,
)
from omx_remote.shared.exceptions import UnsupportedExecutionPayloadError

__all__ = (
    "_load_execution_transport_payload",
    "_normalize_execution_event_payload",
    "_normalize_execution_event_type",
    "_normalize_execution_item_completed_payload",
    "_normalize_execution_item_payload",
    "_normalize_execution_thread_started_payload",
    "_normalize_execution_turn_completed_payload",
    "_normalize_execution_usage_payload",
    "load_execution_payload",
)


def load_execution_payload(
    payload_name: str,
    payload: object,
) -> ExecutionPayload:
    """Loads one execution payload from a raw object boundary.

    Args:
        payload_name [str]: Human-readable payload name included in boundary error messages.
        payload [object]: Raw execution payload from JSONL/event transport.

    Returns:
        ExecutionPayload: Normalized execution payload ready for splitting or contract promotion.

    Raises:
        UnsupportedExecutionPayloadError: Raised when the raw payload is not a JSON object payload.
    """
    if not isinstance(payload, dict):
        raise UnsupportedExecutionPayloadError(
            f"{payload_name} must be a JSON object payload"
        )

    transport_payload: ExecutionTransportPayload = _load_execution_transport_payload(
        payload
    )
    event_type_value: str | None = _normalize_execution_event_type(
        transport_payload.get("type")
    )
    normalized_payload: ExecutionPayload = _normalize_execution_event_payload(
        event_type_value,
        transport_payload,
    )
    return normalized_payload
