"""Pydantic and dynamic value conversion helpers for JSON boundaries."""

import math
from collections.abc import Mapping, Sequence
from typing import final

from pydantic import BaseModel

from omx_remote.adapter_types.json_types import JsonObject, JsonValue
from omx_remote.shared.json_transport import json_object_or_none


def json_value_from_object(value: object, context: str) -> JsonValue:
    """Normalize and validate one dynamic value as a JSON value.

    Args:
        value [object]: Candidate dynamic value.
        context [str]: Human-readable value name for failure messages.

    Returns:
        JsonValue: JSON-compatible value with tuples normalized to lists.
    """
    normalized_value = _normalize_json_value(value)
    if isinstance(normalized_value, _NotJsonValue):
        raise ValueError(f"{context} must be JSON-compatible")
    return normalized_value


def model_json_value(model: BaseModel) -> JsonValue:
    """Dump a Pydantic model to a verified JSON value.

    Args:
        model [BaseModel]: Pydantic model to dump with JSON-mode semantics.

    Returns:
        JsonValue: Verified JSON value suitable for adapter transport.
    """
    raw_payload: object = model.model_dump(mode="json")
    payload = json_value_from_object(
        raw_payload,
        context=f"{model.__class__.__name__} dump",
    )
    return payload


def model_json_object(model: BaseModel) -> JsonObject:
    """Dump a Pydantic model to a verified JSON object.

    Args:
        model [BaseModel]: Pydantic model to dump with JSON-mode semantics.

    Returns:
        JsonObject: Verified JSON object suitable for adapter transport.
    """
    raw_payload: JsonValue = model_json_value(model)
    payload = json_object_or_none(raw_payload)
    if payload is None:
        raise ValueError(f"{model.__class__.__name__} did not dump to a JSON object")
    return payload


@final
class _NotJsonValue:
    """Sentinel type for failed JSON normalization."""


_NOT_JSON_VALUE = _NotJsonValue()


def _normalize_json_value(value: object) -> JsonValue | _NotJsonValue:
    """Normalize tuples to lists and reject non-JSON-compatible values.

    Args:
        value [object]: Candidate JSON transport value.

    Returns:
        JsonValue | object: JSON value or sentinel when invalid.
    """
    if value is None or isinstance(value, str | bool | int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            return _NOT_JSON_VALUE
        return value
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        normalized_items: list[JsonValue] = []
        for item in value:
            normalized_item = _normalize_json_value(item)
            if isinstance(normalized_item, _NotJsonValue):
                return _NOT_JSON_VALUE
            normalized_items.append(normalized_item)
        return normalized_items
    if isinstance(value, Mapping):
        normalized_object: JsonObject = {}
        for key, item in value.items():
            if not isinstance(key, str):
                return _NOT_JSON_VALUE
            normalized_item = _normalize_json_value(item)
            if isinstance(normalized_item, _NotJsonValue):
                return _NOT_JSON_VALUE
            normalized_object[key] = normalized_item
        return normalized_object
    return _NOT_JSON_VALUE
