import re
from typing import cast

import orjson

from omx_remote.adapter_types.json_types import JsonObject, JsonValue

REDACTED_TEXT = "[REDACTED]"
_SENSITIVE_KEY_MARKERS: tuple[str, ...] = (
    "token",
    "password",
    "secret",
    "api_key",
    "apikey",
    "key",
    "header",
    "auth",
    "authorization",
    "bearer",
)
_ASSIGNMENT_RE: re.Pattern[str] = re.compile(
    r"(?i)([\"']?\b(?:token|password|secret|api[_-]?key|key|authorization|auth|header)"
    r"\b[\"']?\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|.*?)"
    r"(?=\s+[\"']?\b[a-zA-Z0-9_.-]+\b[\"']?\s*[:=]|$)"
)
_BEARER_RE: re.Pattern[str] = re.compile(r"(?i)(authorization:\s*bearer\s+)([^\s]+)")
_ARGV_KEYS: frozenset[str] = frozenset({"argv", "native_argv"})


def is_sensitive_key(key: str) -> bool:
    """Return whether a key or CLI flag name likely contains a secret.

    Args:
        key: See function signature.

    Returns:
        See function return annotation."""
    normalized_key: str = key.lower().replace("-", "_")
    sensitive: bool = any(marker in normalized_key for marker in _SENSITIVE_KEY_MARKERS)
    return sensitive


def redact_text(value: str) -> str:
    """Redact common secret patterns from free-form text.

    Args:
        value: See function signature.

    Returns:
        See function return annotation."""
    json_redacted: str | None = _try_redact_json_text(value)
    if json_redacted is not None:
        return json_redacted
    bearer_redacted: str = _BEARER_RE.sub(r"\1[REDACTED]", value)
    redacted_lines: list[str] = [
        _redact_text_line(line) for line in bearer_redacted.splitlines(keepends=True)
    ]
    redacted: str = "".join(redacted_lines)
    return redacted


def _redact_assignment_match(match: re.Match[str]) -> str:
    """Redact one sensitive key assignment while preserving quote style.

    Args:
        match: See function signature.

    Returns:
        See function return annotation."""
    prefix: str = match.group(1)
    raw_value: str = match.group(2)
    stripped_value: str = raw_value.strip()
    if stripped_value.startswith('"') and stripped_value.endswith('"'):
        redacted = f'{prefix}"{REDACTED_TEXT}"'
        return redacted
    if stripped_value.startswith("'") and stripped_value.endswith("'"):
        redacted = f"{prefix}'{REDACTED_TEXT}'"
        return redacted
    redacted = f"{prefix}{REDACTED_TEXT}"
    return redacted


def _redact_text_line(line: str) -> str:
    """Redact one text line, parsing whole-line JSON when possible.

    Args:
        line: See function signature.

    Returns:
        See function return annotation."""
    line_ending = ""
    line_body = line
    if line.endswith("\r\n"):
        line_body = line[:-2]
        line_ending = "\r\n"
    elif line.endswith("\n"):
        line_body = line[:-1]
        line_ending = "\n"
    stripped_line = line_body.strip()
    if stripped_line.startswith(("{", "[")):
        json_redacted: str | None = _try_redact_json_text(stripped_line)
        if json_redacted is not None:
            prefix_length: int = len(line_body) - len(line_body.lstrip())
            prefix: str = line_body[:prefix_length]
            return f"{prefix}{json_redacted}{line_ending}"
    assignment_redacted: str = _ASSIGNMENT_RE.sub(
        _redact_assignment_match,
        line_body,
    )
    return f"{assignment_redacted}{line_ending}"


def _try_redact_json_text(value: str) -> str | None:
    """Redact a JSON object/list string when possible.

    Args:
        value: See function signature.

    Returns:
        See function return annotation."""
    stripped_value: str = value.strip()
    if not stripped_value.startswith(("{", "[")):
        no_json: None = None
        return no_json
    try:
        parsed: JsonValue = orjson.loads(value)
    except orjson.JSONDecodeError:
        no_json = None
        return no_json
    redacted_value: JsonValue = redact_json_value(parsed)
    redacted_text: str = orjson.dumps(redacted_value).decode()
    return redacted_text


def redact_json_value(value: JsonValue) -> JsonValue:
    """Recursively redact secret-looking JSON object keys.

    Args:
        value: See function signature.

    Returns:
        See function return annotation."""
    if isinstance(value, dict):
        redacted_object: JsonObject = {}
        for key, child_value in value.items():
            argv_value: tuple[str, ...] | None = _argv_tuple_for_key(key, child_value)
            if argv_value is not None:
                redacted_argv_values = cast(
                    list[JsonValue], list(redact_argv(argv_value))
                )
                redacted_object[key] = redacted_argv_values
            elif is_sensitive_key(key):
                redacted_object[key] = REDACTED_TEXT
            else:
                redacted_object[key] = redact_json_value(child_value)
        return redacted_object
    if isinstance(value, list):
        redacted_list: list[JsonValue] = [redact_json_value(item) for item in value]
        return redacted_list
    if isinstance(value, str):
        redacted_string: str = redact_text(value)
        return redacted_string
    return value


def _argv_tuple_for_key(key: str, value: JsonValue) -> tuple[str, ...] | None:
    """Return a string argv tuple for argv-shaped JSON fields.

    Args:
        key: See function signature.
        value: See function signature.

    Returns:
        See function return annotation."""
    if key not in _ARGV_KEYS or not isinstance(value, list):
        no_argv: None = None
        return no_argv
    parts: list[str] = []
    for item in value:
        if not isinstance(item, str):
            no_argv = None
            return no_argv
        parts.append(item)
    return tuple(parts)


def redact_json_artifact(value: JsonValue) -> JsonValue:
    """Redact a JSON artifact before durable persistence.

    Args:
        value: See function signature.

    Returns:
        See function return annotation."""
    redacted_value: JsonValue = redact_json_value(value)
    return redacted_value


def redact_argv(argv: tuple[str, ...]) -> tuple[str, ...]:
    """Redact secret-looking CLI argv values before durable persistence.

    Args:
        argv: See function signature.

    Returns:
        See function return annotation."""
    redacted_parts: list[str] = []
    redact_next = False
    for part in argv:
        if redact_next:
            redacted_parts.append(REDACTED_TEXT)
            redact_next = False
            continue
        if part.startswith("--"):
            flag_text: str = part[2:]
            if "=" in flag_text:
                key, _value = flag_text.split("=", 1)
                if is_sensitive_key(key):
                    redacted_parts.append(f"--{key}={REDACTED_TEXT}")
                    continue
            elif is_sensitive_key(flag_text):
                redacted_parts.append(part)
                redact_next = True
                continue
        json_redacted: str | None = _try_redact_json_text(part)
        if json_redacted is not None:
            redacted_parts.append(json_redacted)
        else:
            redacted_parts.append(redact_text(part))
    redacted_argv = tuple(redacted_parts)
    return cast(tuple[str, ...], redacted_argv)
