"""GitHub REST API helpers for cockpit PR evidence."""

from __future__ import annotations

import urllib.error
import urllib.request

import orjson

from omx_remote.adapter_types.json_types import JsonArray, JsonObject, JsonValue
from omx_remote.runtime.cockpit.sources.github_pr_status.credentials import (
    _read_github_token,
)

GITHUB_API_ROOT = "https://api.github.com"
GITHUB_API_PAGE_SIZE = 100


def _read_github_api_json(repo_root: str, api_path: str) -> JsonValue | None:
    """Read one GitHub REST API JSON response.

    Args:
        repo_root [str]: Repository root used for token lookup.
        api_path [str]: API path beginning with `/repos/...`.

    Returns:
        JsonValue | None: Parsed JSON payload when the request succeeds, otherwise None.
    """
    token: str | None = _read_github_token(repo_root)
    if token is None:
        missing_payload: JsonValue | None = None
        return missing_payload

    request = urllib.request.Request(
        f"{GITHUB_API_ROOT}{api_path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "agent-remote-cockpit",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            response_body: bytes = response.read()
    except (OSError, urllib.error.HTTPError, urllib.error.URLError):
        failed_payload: JsonValue | None = None
        return failed_payload

    try:
        parsed_payload = orjson.loads(response_body)
    except orjson.JSONDecodeError:
        malformed_payload: JsonValue | None = None
        return malformed_payload

    payload: JsonValue | None = parsed_payload
    return payload


def _build_paginated_array_path(api_path: str, page_number: int) -> str:
    """Build a GitHub API path with explicit array pagination.

    Args:
        api_path [str]: Base API path to read.
        page_number [int]: One-indexed page number to request.

    Returns:
        str: API path with `per_page` and `page` query parameters.
    """
    separator: str = "?"
    if "?" in api_path:
        separator = "&"

    paginated_path: str = (
        f"{api_path}{separator}per_page={GITHUB_API_PAGE_SIZE}&page={page_number}"
    )
    return paginated_path


def _read_github_paginated_array_json(
    repo_root: str, api_path: str
) -> JsonValue | None:
    """Read every page of a GitHub REST array payload.

    Args:
        repo_root [str]: Repository root used for token lookup.
        api_path [str]: API path beginning with `/repos/...` and returning an array.

    Returns:
        JsonValue | None: Combined array payload, or None if any required page fails.
    """
    combined_array: JsonArray = []
    page_number: int = 1
    while True:
        page_path: str = _build_paginated_array_path(api_path, page_number)
        page_payload: JsonValue | None = _read_github_api_json(repo_root, page_path)
        page_array: JsonArray | None = _as_json_array(page_payload)
        if page_array is None:
            missing_page: JsonValue | None = None
            return missing_page

        combined_array.extend(page_array)
        if len(page_array) < GITHUB_API_PAGE_SIZE:
            paginated_payload: JsonValue | None = combined_array
            return paginated_payload

        page_number += 1


def _read_github_paginated_object_array_json(
    repo_root: str,
    api_path: str,
    array_key: str,
) -> JsonValue | None:
    """Read every page of a GitHub REST object-wrapped array payload.

    Args:
        repo_root [str]: Repository root used for token lookup.
        api_path [str]: API path beginning with `/repos/...` and returning an object.
        array_key [str]: Object key that contains the paginated array.

    Returns:
        JsonValue | None: Object with the combined array payload, or None on page failure.
    """
    combined_array: JsonArray = []
    page_number: int = 1
    while True:
        page_path: str = _build_paginated_array_path(api_path, page_number)
        page_payload: JsonValue | None = _read_github_api_json(repo_root, page_path)
        page_object: JsonObject | None = _as_json_object(page_payload)
        if page_object is None:
            missing_page: JsonValue | None = None
            return missing_page

        page_array: JsonArray | None = _as_json_array(page_object.get(array_key))
        if page_array is None:
            malformed_page: JsonValue | None = None
            return malformed_page

        combined_array.extend(page_array)
        if len(page_array) < GITHUB_API_PAGE_SIZE:
            paginated_payload: JsonObject = {array_key: combined_array}
            combined_payload: JsonValue | None = paginated_payload
            return combined_payload

        page_number += 1


def _as_json_object(raw_value: JsonValue | None) -> JsonObject | None:
    """Narrow a JSON value to an object.

    Args:
        raw_value [JsonValue | None]: Raw JSON value.

    Returns:
        JsonObject | None: The object value when present, otherwise None.
    """
    if isinstance(raw_value, dict):
        object_value: JsonObject | None = raw_value
        return object_value

    missing_object: JsonObject | None = None
    return missing_object


def _as_json_array(raw_value: JsonValue | None) -> JsonArray | None:
    """Narrow a JSON value to an array.

    Args:
        raw_value [JsonValue | None]: Raw JSON value.

    Returns:
        JsonArray | None: The array value when present, otherwise None.
    """
    if isinstance(raw_value, list):
        array_value: JsonArray | None = raw_value
        return array_value

    missing_array: JsonArray | None = None
    return missing_array


def _as_non_empty_text(raw_value: JsonValue | None) -> str | None:
    """Narrow a JSON value to non-empty text.

    Args:
        raw_value [JsonValue | None]: Raw JSON value.

    Returns:
        str | None: Non-empty string when available, otherwise None.
    """
    if not isinstance(raw_value, str):
        missing_text: str | None = None
        return missing_text

    if raw_value == "":
        empty_text: str | None = None
        return empty_text

    text_value: str | None = raw_value
    return text_value


def _as_positive_int(raw_value: JsonValue | None) -> int | None:
    """Narrow a JSON value to a positive integer.

    Args:
        raw_value [JsonValue | None]: Raw JSON value.

    Returns:
        int | None: Positive integer when available, otherwise None.
    """
    if not isinstance(raw_value, int):
        missing_int: int | None = None
        return missing_int

    if raw_value < 1:
        invalid_int: int | None = None
        return invalid_int

    int_value: int | None = raw_value
    return int_value
