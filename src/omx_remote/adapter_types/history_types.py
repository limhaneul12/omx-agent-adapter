from typing import TypedDict

import msgspec

from omx_remote.schemas.history_session_schemas import SessionSearchResultSnapshot


class SessionSearchResultSpec(msgspec.Struct, kw_only=True):
    """Represents one decoded session-search result item before normalization."""

    session_id: str | None = None
    timestamp: str | None = None
    cwd: str | None = None
    record_type: str | None = None
    line_number: int | None = None
    snippet: str | None = None


class SessionSearchSpec(msgspec.Struct, kw_only=True):
    """Represents the decoded session-search transport payload."""

    query: str | None = None
    searched_files: int | None = None
    matched_sessions: int | None = None
    results: list[SessionSearchResultSpec] | None = None


class SessionSearchTransportResultPayload(TypedDict):
    """Represents the stable observed subset for one session-search result item."""

    session_id: str | None
    timestamp: str | None
    cwd: str | None
    record_type: str | None
    line_number: int | None
    snippet: str | None


type SessionSearchTransportResults = (
    list[SessionSearchResultSpec] | list[SessionSearchTransportResultPayload]
)
type SessionSearchNormalizedResults = list[SessionSearchResultSnapshot]


class SessionSearchTransportPayload(TypedDict):
    """Represents the stable top-level transport subset for session search."""

    query: str
    searched_files: int
    matched_sessions: int
    results: SessionSearchTransportResults


class SessionSearchNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for session search."""

    query: str
    searched_files: int
    matched_sessions: int
    results: SessionSearchNormalizedResults
