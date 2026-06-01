from typing import cast

from omx_remote.adapter_types.execution_types import (
    ExecutionExtraTransportPayload,
    ExecutionItemCompletedTransportPayload,
    ExecutionItemSpec,
    ExecutionItemTransportPayload,
    ExecutionThreadStartedTransportPayload,
    ExecutionTransportPayload,
    ExecutionTransportSpec,
    ExecutionTurnCompletedTransportPayload,
    ExecutionUsageSpec,
    ExecutionUsageTransportPayload,
)
from omx_remote.adapter_types.type_contract import (
    execution_payload_normalizer_contract_type,
    execution_transport_contract_type,
)
from omx_remote.adapter_types.type_contract.execution_contract_type import (
    KNOWN_EXECUTION_EVENT_TYPES,
)
from omx_remote.adapter_types.type_contract.execution_payload_normalizer_contract_type import (
    ExecutionEventPayloadNormalizer,
)
from omx_remote.execution.payload_conversion import (
    _convert_msgspec_optional_int,
    _convert_msgspec_optional_mapping,
    _convert_msgspec_optional_str,
    _copy_passthrough_fields,
    _execution_item_spec_to_payload,
    _execution_transport_spec_to_payload,
    _execution_usage_spec_to_payload,
)
from omx_remote.shared.exceptions import UnsupportedExecutionPayloadError
from omx_remote.shared.omx_enums.execution_enums import ExecutionEventKind


def _normalize_execution_extra_payload(
    extra_payload: object,
) -> ExecutionExtraTransportPayload | None:
    """Normalizes raw execution diagnostic metadata into a mapping-shaped field.

    Args:
        extra_payload [object]: Raw `extra` value from an execution transport payload.

    Returns:
        ExecutionExtraTransportPayload | None: Mapping-shaped diagnostic metadata, otherwise `None`.
    """
    extra_mapping: dict[str, object] | None = _convert_msgspec_optional_mapping(
        extra_payload
    )
    if extra_mapping is None:
        missing_extra: None = None
        return missing_extra

    normalized_extra_payload = cast(ExecutionExtraTransportPayload, extra_mapping)
    return normalized_extra_payload


def _normalize_execution_event_type(event_type: object) -> str | None:
    """Normalizes one raw execution event type into a string field.

    Args:
        event_type [object]: Raw `type` field read from an execution transport payload.

    Returns:
        str | None: Known or passthrough event type text, or `None` when the raw value is not a string.
    """
    normalized_event_type: str | None = _convert_msgspec_optional_str(event_type)
    if normalized_event_type is None:
        missing_event_type: None = None
        return missing_event_type

    if normalized_event_type in KNOWN_EXECUTION_EVENT_TYPES:
        known_event_type: str = normalized_event_type
        return known_event_type

    passthrough_event_type: str = normalized_event_type
    return passthrough_event_type


def _normalize_execution_item_payload(
    item_payload: object,
) -> ExecutionItemTransportPayload:
    """Normalizes one raw execution item payload into its stable field contract.

    Args:
        item_payload [object]: Raw `item` value from an execution event payload.

    Returns:
        ExecutionItemTransportPayload: Item payload containing only validated stable fields.

    Raises:
        UnsupportedExecutionPayloadError: Raised when the item value is not a JSON object payload.
    """
    item_mapping: dict[str, object] | None = _convert_msgspec_optional_mapping(
        item_payload
    )
    if item_mapping is None:
        raise UnsupportedExecutionPayloadError(
            "execution item payload must be a JSON object payload"
        )

    passthrough_fields: dict[str, object] = _copy_passthrough_fields(
        item_mapping,
        execution_transport_contract_type.EXECUTION_ITEM_STABLE_FIELD_KEYS,
    )
    item_spec = ExecutionItemSpec(
        id=_convert_msgspec_optional_str(item_mapping.get("id")),
        type=_convert_msgspec_optional_str(item_mapping.get("type")),
        text=_convert_msgspec_optional_str(item_mapping.get("text")),
        tool_name=_convert_msgspec_optional_str(item_mapping.get("tool_name")),
        call_id=_convert_msgspec_optional_str(item_mapping.get("call_id")),
        arguments=_convert_msgspec_optional_str(item_mapping.get("arguments")),
        command=_convert_msgspec_optional_str(item_mapping.get("command")),
        aggregated_output=_convert_msgspec_optional_str(
            item_mapping.get("aggregated_output")
        ),
        exit_code=_convert_msgspec_optional_int(item_mapping.get("exit_code")),
        status=_convert_msgspec_optional_str(item_mapping.get("status")),
    )
    stable_payload: ExecutionItemTransportPayload = _execution_item_spec_to_payload(
        item_spec
    )
    passthrough_fields.update(stable_payload)
    normalized_payload = cast(ExecutionItemTransportPayload, passthrough_fields)
    return normalized_payload


def _normalize_execution_usage_payload(
    usage_payload: object,
) -> ExecutionUsageTransportPayload:
    """Normalizes one raw execution usage payload into its stable field contract.

    Args:
        usage_payload [object]: Raw `usage` value from a turn-completed event payload.

    Returns:
        ExecutionUsageTransportPayload: Usage payload containing only validated token counter fields.

    Raises:
        UnsupportedExecutionPayloadError: Raised when the usage value is not a JSON object payload.
    """
    if not isinstance(usage_payload, dict):
        raise UnsupportedExecutionPayloadError(
            "execution usage payload must be a JSON object payload"
        )

    usage_spec = ExecutionUsageSpec(
        input_tokens=_convert_msgspec_optional_int(usage_payload.get("input_tokens")),
        cached_input_tokens=_convert_msgspec_optional_int(
            usage_payload.get("cached_input_tokens")
        ),
        output_tokens=_convert_msgspec_optional_int(usage_payload.get("output_tokens")),
        reasoning_output_tokens=_convert_msgspec_optional_int(
            usage_payload.get("reasoning_output_tokens")
        ),
    )
    normalized_usage_payload: ExecutionUsageTransportPayload = (
        _execution_usage_spec_to_payload(usage_spec)
    )
    return normalized_usage_payload


def _normalize_execution_thread_started_payload(
    payload: ExecutionTransportPayload,
) -> ExecutionThreadStartedTransportPayload:
    """Normalizes one thread-started execution payload into its stable subset.

    Args:
        payload [ExecutionTransportPayload]: Top-level execution payload containing a thread-started event.

    Returns:
        ExecutionThreadStartedTransportPayload: Thread-started subset with normalized thread identifier text.
    """
    thread_id_value: str | None = _convert_msgspec_optional_str(
        payload.get("thread_id")
    )
    if thread_id_value is None:
        missing_thread_id: str = ""
        normalized_payload = ExecutionThreadStartedTransportPayload(
            type=ExecutionEventKind.THREAD_STARTED,
            thread_id=missing_thread_id,
        )
        return normalized_payload

    normalized_payload = ExecutionThreadStartedTransportPayload(
        type=ExecutionEventKind.THREAD_STARTED,
        thread_id=thread_id_value,
    )
    return normalized_payload


def _normalize_execution_turn_completed_payload(
    payload: ExecutionTransportPayload,
) -> ExecutionTurnCompletedTransportPayload:
    """Normalizes one turn-completed execution payload into its stable subset.

    Args:
        payload [ExecutionTransportPayload]: Top-level execution payload containing a turn-completed event.

    Returns:
        ExecutionTurnCompletedTransportPayload: Turn-completed subset with normalized usage counters.
    """
    usage_value: object | None = payload.get("usage")
    usage_mapping: dict[str, object] | None = _convert_msgspec_optional_mapping(
        usage_value
    )
    if usage_mapping is None:
        normalized_usage_payload: ExecutionUsageTransportPayload = {}
    else:
        normalized_usage_payload = _normalize_execution_usage_payload(usage_mapping)

    normalized_payload = ExecutionTurnCompletedTransportPayload(
        type=ExecutionEventKind.TURN_COMPLETED,
        usage=normalized_usage_payload,
    )
    return normalized_payload


def _normalize_execution_item_completed_payload(
    payload: ExecutionTransportPayload,
) -> ExecutionItemCompletedTransportPayload:
    """Normalizes one item-completed execution payload into its stable subset.

    Args:
        payload [ExecutionTransportPayload]: Top-level execution payload containing an item-completed event.

    Returns:
        ExecutionItemCompletedTransportPayload: Item-completed subset with normalized nested item fields.
    """
    item_value: object | None = payload.get("item")
    item_mapping: dict[str, object] | None = _convert_msgspec_optional_mapping(
        item_value
    )
    if item_mapping is None:
        normalized_item_payload: ExecutionItemTransportPayload = {}
    else:
        normalized_item_payload = _normalize_execution_item_payload(item_mapping)

    normalized_payload = ExecutionItemCompletedTransportPayload(
        type=ExecutionEventKind.ITEM_COMPLETED,
        item=normalized_item_payload,
    )
    return normalized_payload


def _select_execution_event_payload_normalizer(
    event_type: str | None,
) -> ExecutionEventPayloadNormalizer | None:
    """Selects the event-specific payload normalizer for a known execution event type.

    Args:
        event_type [str | None]: Normalized top-level execution event type text.

    Returns:
        ExecutionEventPayloadNormalizer | None: Event-specific normalizer when the type is known and field-specific, otherwise `None`.
    """
    if event_type is None:
        missing_normalizer: None = None
        return missing_normalizer

    try:
        event_kind = ExecutionEventKind(event_type)
    except ValueError:
        missing_normalizer = None
        return missing_normalizer

    normalizer: ExecutionEventPayloadNormalizer | None = (
        execution_payload_normalizer_contract_type.EXECUTION_EVENT_PAYLOAD_NORMALIZERS.get(
            event_kind
        )
    )
    return normalizer


def _normalize_execution_event_payload(
    event_type: str | None,
    payload: ExecutionTransportPayload,
) -> ExecutionTransportPayload:
    """Normalizes event-kind-specific execution payload fields into a stable subset.

    Args:
        event_type [str | None]: Normalized top-level execution event type text.
        payload [ExecutionTransportPayload]: Top-level execution transport payload before event-specific field merging.

    Returns:
        ExecutionTransportPayload: Normalized top-level payload with validated common fields and event-specific fields.
    """
    normalized_payload: ExecutionTransportPayload = _load_execution_transport_payload(
        payload
    )
    normalizer: ExecutionEventPayloadNormalizer | None = (
        _select_execution_event_payload_normalizer(event_type)
    )
    if normalizer is None:
        return normalized_payload

    merge_payload: ExecutionTransportPayload = normalizer(normalized_payload)
    normalized_payload.update(merge_payload)
    return normalized_payload


def _load_execution_transport_payload(payload: object) -> ExecutionTransportPayload:
    """Loads one raw execution transport payload into the owned top-level subset.

    Args:
        payload [object]: Raw execution payload from JSONL/event transport before stable promotion.

    Returns:
        ExecutionTransportPayload: Top-level payload containing only validated stable transport fields.

    Raises:
        UnsupportedExecutionPayloadError: Raised when the raw payload is not a JSON object payload.
    """
    payload_mapping: dict[str, object] | None = _convert_msgspec_optional_mapping(
        payload
    )
    if payload_mapping is None:
        raise UnsupportedExecutionPayloadError(
            "execution payload must be a JSON object payload"
        )

    passthrough_fields: dict[str, object] = _copy_passthrough_fields(
        payload_mapping,
        execution_transport_contract_type.EXECUTION_TRANSPORT_STABLE_FIELD_KEYS,
    )
    item_mapping: dict[str, object] | None = _convert_msgspec_optional_mapping(
        payload_mapping.get("item")
    )
    usage_mapping: dict[str, object] | None = _convert_msgspec_optional_mapping(
        payload_mapping.get("usage")
    )
    if item_mapping is None:
        normalized_item_payload: ExecutionItemTransportPayload | None = None
    else:
        normalized_item_payload = _normalize_execution_item_payload(item_mapping)
    if usage_mapping is None:
        normalized_usage_payload: ExecutionUsageTransportPayload | None = None
    else:
        normalized_usage_payload = _normalize_execution_usage_payload(usage_mapping)

    transport_spec = ExecutionTransportSpec(
        type=_normalize_execution_event_type(payload_mapping.get("type")),
        text=_convert_msgspec_optional_str(payload_mapping.get("text")),
        item=normalized_item_payload,
        tool_name=_convert_msgspec_optional_str(payload_mapping.get("tool_name")),
        call_id=_convert_msgspec_optional_str(payload_mapping.get("call_id")),
        arguments=_convert_msgspec_optional_str(payload_mapping.get("arguments")),
        command=_convert_msgspec_optional_str(payload_mapping.get("command")),
        aggregated_output=_convert_msgspec_optional_str(
            payload_mapping.get("aggregated_output")
        ),
        exit_code=_convert_msgspec_optional_int(payload_mapping.get("exit_code")),
        status=_convert_msgspec_optional_str(payload_mapping.get("status")),
        id=_convert_msgspec_optional_str(payload_mapping.get("id")),
        extra=_normalize_execution_extra_payload(payload_mapping.get("extra")),
        kind=_convert_msgspec_optional_str(payload_mapping.get("kind")),
        thread_id=_convert_msgspec_optional_str(payload_mapping.get("thread_id")),
        usage=normalized_usage_payload,
    )
    stable_payload: ExecutionTransportPayload = _execution_transport_spec_to_payload(
        transport_spec
    )
    passthrough_fields.update(stable_payload)
    normalized_payload = cast(ExecutionTransportPayload, passthrough_fields)
    return normalized_payload
