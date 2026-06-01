import orjson

from omx_remote.adapter_types.json_types import JsonObject, JsonValue
from omx_remote.shared.json_transport import (
    has_non_finite_float,
    is_json_object,
    is_json_value,
)


def _round_trip_json_payload(value: object, error_message: str) -> JsonValue:
    """Round-trip a dynamic payload without silently coercing invalid floats.

    Args:
        value [object]: Dynamic SDK or process payload.
        error_message [str]: Error message when payload is not JSON-compatible.

    Returns:
        JsonValue: JSON-compatible payload.
    """
    if has_non_finite_float(value):
        raise ValueError(error_message)
    payload: object = orjson.loads(orjson.dumps(value))
    if not is_json_value(payload):
        raise ValueError(error_message)
    json_payload: JsonValue = payload
    return json_payload


def normalize_mcp_json_object(value: object, error_message: str) -> JsonObject:
    """Round-trip a dynamic MCP payload into a JSON object.

    Args:
        value [object]: Dynamic SDK or process payload.
        error_message [str]: Error message when the payload is not an object.

    Returns:
        JsonObject: JSON-compatible object.
    """
    payload = _round_trip_json_payload(value, error_message)
    if not is_json_object(payload):
        raise ValueError(error_message)
    return payload


def normalize_mcp_json_object_list(
    value: object, error_message: str
) -> list[JsonObject]:
    """Round-trip a dynamic MCP payload into a list of JSON objects.

    Args:
        value [object]: Dynamic process payload.
        error_message [str]: Error message when the payload is not an object list.

    Returns:
        list[JsonObject]: JSON-compatible object list.
    """
    payload = _round_trip_json_payload(value, error_message)
    if not isinstance(payload, list):
        raise ValueError(error_message)

    objects: list[JsonObject] = []
    for item in payload:
        if not is_json_object(item):
            raise ValueError(error_message)
        objects.append(item)

    return objects
