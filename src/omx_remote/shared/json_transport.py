import math
from typing import TypeGuard

from omx_remote.adapter_types.json_types import JsonObject, JsonValue


def is_json_value(value: object) -> TypeGuard[JsonValue]:
    """Return whether a value is JSON-compatible transport data.

    Args:
        value [object]: Candidate value from a dynamic transport boundary.

    Returns:
        TypeGuard[JsonValue]: Whether the value is a valid JSON value.
    """
    if value is None or isinstance(value, str | bool | int):
        is_valid = True
        return is_valid
    if isinstance(value, float):
        is_valid = math.isfinite(value)
        return is_valid
    if isinstance(value, list):
        is_valid = all(is_json_value(item) for item in value)
        return is_valid
    if isinstance(value, dict):
        is_valid = all(
            isinstance(key, str) and is_json_value(item)
            for key, item in value.items()
        )
        return is_valid
    is_valid = False
    return is_valid


def is_json_object(value: object) -> TypeGuard[JsonObject]:
    """Return whether a value is a JSON object.

    Args:
        value [object]: Candidate value from a dynamic transport boundary.

    Returns:
        TypeGuard[JsonObject]: Whether the value is a JSON object.
    """
    if not isinstance(value, dict):
        is_valid = False
        return is_valid
    is_valid = all(
        isinstance(key, str) and is_json_value(item) for key, item in value.items()
    )
    return is_valid


def has_non_finite_float(value: object) -> bool:
    """Return whether a nested dynamic payload contains NaN or infinity.

    Args:
        value [object]: Candidate dynamic payload before JSON serialization.

    Returns:
        bool: Whether the payload contains a non-finite float.
    """
    if isinstance(value, float):
        return not math.isfinite(value)
    if isinstance(value, dict):
        has_invalid_float = any(
            has_non_finite_float(key) or has_non_finite_float(item)
            for key, item in value.items()
        )
        return has_invalid_float
    if isinstance(value, list | tuple):
        has_invalid_float = any(has_non_finite_float(item) for item in value)
        return has_invalid_float
    return False


def json_object_or_none(value: object) -> JsonObject | None:
    """Normalize a dynamic candidate to a JSON object when possible.

    Args:
        value [object]: Candidate value from a dynamic transport boundary.

    Returns:
        JsonObject | None: JSON object when the candidate is valid.
    """
    if not is_json_object(value):
        missing_object: None = None
        return missing_object
    json_object: JsonObject = value
    return json_object
