from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

import orjson
from comx_harness.schemas.lifecycle_schemas import EventReport

_TEAM_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
_TEAM_FIELD = re.compile(
    r"(?:team_name|teamName)\s*[:=]\s*[\"']?([a-z0-9][a-z0-9-]{0,63})"
)
_TEAM_COMMAND = re.compile(
    r"omx\s+team\s+(?:status|resume|shutdown|await)\s+([a-z0-9][a-z0-9-]{0,63})"
)


def validate_omx_team_name(team_name: str) -> str:
    normalized = team_name.strip()
    if not _TEAM_NAME.fullmatch(normalized):
        raise ValueError(f"invalid OMX team name: {team_name}")
    return normalized


def discover_omx_team_names(events: EventReport) -> tuple[str, ...]:
    names: set[str] = set()
    for event in events.events:
        _collect_from_text(event.message, names)
        if event.provider_payload_json:
            try:
                payload = orjson.loads(event.provider_payload_json)
            except orjson.JSONDecodeError:
                continue
            _collect_from_payload(payload, names)
    return tuple(sorted(names))


def _collect_from_text(text: str, names: set[str]) -> None:
    names.update(_TEAM_FIELD.findall(text))
    names.update(_TEAM_COMMAND.findall(text))


def _collect_from_payload(value: object, names: set[str]) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key in {"team_name", "teamName"} and isinstance(child, str):
                if _TEAM_NAME.fullmatch(child):
                    names.add(child)
            else:
                _collect_from_payload(child, names)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for child in value:
            _collect_from_payload(child, names)
    elif isinstance(value, str):
        _collect_from_text(value, names)
