from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass

import orjson
from comx_harness.ade.codex_subagent_toml import relative_agent_config_file
from comx_harness.schemas.codex_subagent_schemas import (
    CodexSubagentRegistrationSpec,
    CodexSubagentSpec,
)

_MARKER_KEY = "__comx_agent_toml_marker__"
_MAX_THREADS_KEY = "max_concurrent_threads_per_session"
_LEGACY_MAX_THREADS_KEY = "max_threads"
_BARE_KEY = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True, slots=True)
class _Header:
    line_index: int
    path: tuple[str, ...]
    is_array: bool


def update_project_config(
    current: str,
    spec: CodexSubagentRegistrationSpec,
) -> str:
    _parse_config(current)
    updated = current
    for agent in spec.agents:
        updated = _remove_agent_registration(updated, agent.name)
    if spec.max_concurrent_threads_per_session is not None:
        updated = _set_max_threads(
            updated,
            spec.max_concurrent_threads_per_session,
        )

    rendered_sections = "\n\n".join(
        _render_registration_section(agent) for agent in spec.agents
    )
    updated = updated.rstrip()
    if updated:
        updated = f"{updated}\n\n{rendered_sections}\n"
    else:
        updated = f"{rendered_sections}\n"
    _parse_config(updated)
    return updated


def _remove_agent_registration(text: str, name: str) -> str:
    parsed = _parse_config(text)
    if not _has_agent_registration(parsed, name):
        return text

    lines = text.splitlines(keepends=True)
    headers = _headers(lines)
    removed_lines: set[int] = set()
    target_path = ("agents", name)
    for header_index, header in enumerate(headers):
        if header.path[:2] != target_path:
            continue
        section_end = (
            headers[header_index + 1].line_index
            if header_index + 1 < len(headers)
            else len(lines)
        )
        removed_lines.update(range(header.line_index, section_end))

    for line_index, table_path in _assignment_contexts(lines, headers):
        if line_index in removed_lines:
            continue
        assignment_paths = _assignment_paths(lines[line_index], table_path)
        matching_paths = tuple(
            path for path in assignment_paths if path[:2] == target_path
        )
        if matching_paths and len(matching_paths) == len(assignment_paths):
            removed_lines.add(line_index)

    updated = "".join(
        line for index, line in enumerate(lines) if index not in removed_lines
    )
    if _has_agent_registration(_parse_config(updated), name):
        raise ValueError(
            f"Cannot safely update agents.{name}: unsupported TOML declaration shape"
        )
    return updated


def _set_max_threads(text: str, value: int) -> str:
    lines = text.splitlines(keepends=True)
    headers = _headers(lines)
    max_paths = {
        ("agents", _MAX_THREADS_KEY),
        ("agents", _LEGACY_MAX_THREADS_KEY),
    }
    matches: list[tuple[int, tuple[str, ...]]] = []
    for line_index, table_path in _assignment_contexts(lines, headers):
        assignment_paths = _assignment_paths(lines[line_index], table_path)
        matching_paths = tuple(path for path in assignment_paths if path in max_paths)
        if not matching_paths:
            continue
        if len(matching_paths) != len(assignment_paths):
            raise ValueError(
                "Cannot safely update Codex max threads inside a compound TOML value"
            )
        matches.append((line_index, table_path))

    if matches:
        first_index, first_context = matches[0]
        if first_context == ("agents",):
            assignment = f"{_MAX_THREADS_KEY} = {value}\n"
        elif first_context == ():
            assignment = f"agents.{_MAX_THREADS_KEY} = {value}\n"
        else:
            raise ValueError("Cannot safely update nested Codex max threads")
        lines[first_index] = assignment
        for line_index, _ in matches[1:]:
            lines[line_index] = ""
        updated = "".join(lines)
        return updated

    parsed = _parse_config(text)
    agents = parsed.get("agents")
    if isinstance(agents, dict) and (
        _MAX_THREADS_KEY in agents or _LEGACY_MAX_THREADS_KEY in agents
    ):
        raise ValueError("Cannot safely locate the existing Codex max threads setting")

    agents_header = next(
        (
            header
            for header in headers
            if not header.is_array and header.path == ("agents",)
        ),
        None,
    )
    if agents_header is not None:
        lines.insert(
            agents_header.line_index + 1,
            f"{_MAX_THREADS_KEY} = {value}\n",
        )
    else:
        first_header_index = headers[0].line_index if headers else len(lines)
        lines.insert(
            first_header_index,
            f"agents.{_MAX_THREADS_KEY} = {value}\n\n",
        )
    updated = "".join(lines)
    return updated


def _headers(lines: list[str]) -> tuple[_Header, ...]:
    active_lines = _active_line_starts(lines)
    headers: list[_Header] = []
    for line_index, line in enumerate(lines):
        if not active_lines[line_index]:
            continue
        header = _parse_header(line_index, line)
        if header is not None:
            headers.append(header)
    return tuple(headers)


def _parse_header(line_index: int, line: str) -> _Header | None:
    stripped = line.lstrip()
    if not stripped.startswith("["):
        return None
    is_array = stripped.startswith("[[")
    try:
        parsed = tomllib.loads(f"{line.rstrip()}\n{_MARKER_KEY} = true\n")
    except tomllib.TOMLDecodeError:
        return None
    marker_path = _find_marker_path(parsed)
    if marker_path is None:
        return None
    header = _Header(
        line_index=line_index,
        path=marker_path,
        is_array=is_array,
    )
    return header


def _find_marker_path(value: object) -> tuple[str, ...] | None:
    if isinstance(value, dict):
        if _MARKER_KEY in value:
            return ()
        for key, child in value.items():
            child_path = _find_marker_path(child)
            if child_path is not None:
                return (str(key), *child_path)
    elif isinstance(value, list):
        for child in value:
            child_path = _find_marker_path(child)
            if child_path is not None:
                return child_path
    return None


def _assignment_contexts(
    lines: list[str],
    headers: tuple[_Header, ...],
) -> tuple[tuple[int, tuple[str, ...]], ...]:
    header_by_line = {header.line_index: header for header in headers}
    active_lines = _active_line_starts(lines)
    current_table: tuple[str, ...] = ()
    contexts: list[tuple[int, tuple[str, ...]]] = []
    for line_index, line in enumerate(lines):
        header = header_by_line.get(line_index)
        if header is not None:
            current_table = header.path
            continue
        if active_lines[line_index] and "=" in line:
            contexts.append((line_index, current_table))
    return tuple(contexts)


def _assignment_paths(
    line: str,
    table_path: tuple[str, ...],
) -> tuple[tuple[str, ...], ...]:
    prefix = ""
    if table_path:
        rendered_path = ".".join(_toml_key(part) for part in table_path)
        prefix = f"[{rendered_path}]\n"
    try:
        parsed = tomllib.loads(f"{prefix}{line}")
    except tomllib.TOMLDecodeError:
        return ()
    paths = tuple(_leaf_paths(parsed))
    return paths


def _leaf_paths(
    value: object,
    prefix: tuple[str, ...] = (),
) -> tuple[tuple[str, ...], ...]:
    if isinstance(value, dict):
        if not value:
            return (prefix,)
        paths: list[tuple[str, ...]] = []
        for key, child in value.items():
            paths.extend(_leaf_paths(child, (*prefix, str(key))))
        return tuple(paths)
    return (prefix,)


def _active_line_starts(lines: list[str]) -> tuple[bool, ...]:
    delimiter: str | None = None
    active: list[bool] = []
    for line in lines:
        active.append(delimiter is None)
        delimiter = _multiline_delimiter_after(line, delimiter)
    return tuple(active)


def _multiline_delimiter_after(line: str, delimiter: str | None) -> str | None:
    index = 0
    quote: str | None = None
    while index < len(line):
        if delimiter is not None:
            closing_index = line.find(delimiter, index)
            if closing_index < 0:
                return delimiter
            if delimiter == '"""' and _is_escaped(line, closing_index):
                index = closing_index + 1
                continue
            delimiter = None
            index = closing_index + 3
            continue

        character = line[index]
        if quote is None and character == "#":
            break
        if quote is None and line.startswith(('"""', "'''"), index):
            delimiter = line[index : index + 3]
            index += 3
            continue
        if quote is None and character in {'"', "'"}:
            quote = character
            index += 1
            continue
        if quote == '"' and character == "\\":
            index += 2
            continue
        if quote is not None and character == quote:
            quote = None
        index += 1
    return delimiter


def _is_escaped(text: str, index: int) -> bool:
    backslashes = 0
    cursor = index - 1
    while cursor >= 0 and text[cursor] == "\\":
        backslashes += 1
        cursor -= 1
    return backslashes % 2 == 1


def _has_agent_registration(config: dict[str, object], name: str) -> bool:
    agents = config.get("agents")
    exists = isinstance(agents, dict) and name in agents
    return exists


def _parse_config(text: str) -> dict[str, object]:
    try:
        parsed = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f"Invalid existing Codex TOML: {error}") from error
    return parsed


def _render_registration_section(agent: CodexSubagentSpec) -> str:
    section = "\n".join(
        (
            f"[agents.{agent.name}]",
            f"description = {_toml_string(agent.description)}",
            f"config_file = {_toml_string(relative_agent_config_file(agent.name))}",
        )
    )
    return section


def _toml_key(value: str) -> str:
    if _BARE_KEY.fullmatch(value) is not None:
        return value
    return _toml_string(value)


def _toml_string(value: str) -> str:
    encoded = orjson.dumps(value).decode("utf-8")
    return encoded
