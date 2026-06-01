from typing import cast

import msgspec

from omx_remote.adapter_types.execution_types import (
    ExecutionItemSpec,
    ExecutionItemTransportPayload,
    ExecutionTransportPayload,
    ExecutionTransportSpec,
    ExecutionUsageSpec,
    ExecutionUsageTransportPayload,
)


def _copy_passthrough_fields(
    payload: dict[str, object],
    stable_field_keys: frozenset[str],
) -> dict[str, object]:
    """Copies raw fields that are outside the validated stable subset.

    Args:
        payload [dict[str, object]]: Raw JSON object payload from the execution transport boundary.
        stable_field_keys [frozenset[str]]: Keys normalized through explicit msgspec-backed fields.

    Returns:
        dict[str, object]: Raw passthrough fields retained for heterogeneous OMX variants.
    """
    passthrough_fields: dict[str, object] = {
        key: value for key, value in payload.items() if key not in stable_field_keys
    }
    return passthrough_fields


def _convert_msgspec_optional_str(value: object) -> str | None:
    """Converts one optional raw value into a string field.

    Args:
        value [object]: Raw transport value inspected for a string field.

    Returns:
        str | None: Converted string value when the raw value matches the field contract, otherwise `None`.
    """
    try:
        converted_value: str = msgspec.convert(value, str)
    except msgspec.ValidationError:
        missing_value: None = None
        return missing_value

    return converted_value


def _convert_msgspec_optional_int(value: object) -> int | None:
    """Converts one optional raw value into an integer field.

    Args:
        value [object]: Raw transport value inspected for an integer field.

    Returns:
        int | None: Converted integer value when the raw value matches the field contract, otherwise `None`.
    """
    try:
        converted_value: int = msgspec.convert(value, int)
    except msgspec.ValidationError:
        missing_value: None = None
        return missing_value

    return converted_value


def _convert_msgspec_optional_mapping(value: object) -> dict[str, object] | None:
    """Converts one optional raw value into a string-keyed mapping.

    Args:
        value [object]: Raw transport value inspected for a nested JSON object field.

    Returns:
        dict[str, object] | None: Converted mapping when the raw value is object-shaped, otherwise `None`.
    """
    if not isinstance(value, dict):
        missing_mapping: None = None
        return missing_mapping

    converted_mapping: dict[str, object] = cast(dict[str, object], value)
    return converted_mapping


def _execution_usage_spec_to_payload(
    usage_spec: ExecutionUsageSpec,
) -> ExecutionUsageTransportPayload:
    """Converts a usage msgspec contract into the execution TypedDict payload.

    Args:
        usage_spec [ExecutionUsageSpec]: Msgspec contract carrying validated token counter fields.

    Returns:
        ExecutionUsageTransportPayload: TypedDict payload containing only validated usage fields.
    """
    payload = cast(ExecutionUsageTransportPayload, msgspec.to_builtins(usage_spec))
    return payload


def _execution_item_spec_to_payload(
    item_spec: ExecutionItemSpec,
) -> ExecutionItemTransportPayload:
    """Converts an item msgspec contract into the execution TypedDict payload.

    Args:
        item_spec [ExecutionItemSpec]: Msgspec contract carrying validated item fields.

    Returns:
        ExecutionItemTransportPayload: TypedDict payload containing only validated item fields.
    """
    payload = cast(ExecutionItemTransportPayload, msgspec.to_builtins(item_spec))
    return payload


def _execution_transport_spec_to_payload(
    transport_spec: ExecutionTransportSpec,
) -> ExecutionTransportPayload:
    """Converts a top-level msgspec contract into the execution TypedDict payload.

    Args:
        transport_spec [ExecutionTransportSpec]: Msgspec contract carrying validated top-level event fields.

    Returns:
        ExecutionTransportPayload: TypedDict payload containing only validated top-level fields.
    """
    payload = cast(ExecutionTransportPayload, msgspec.to_builtins(transport_spec))
    return payload
