from typing import TypedDict

import msgspec

from omx_remote.schemas.history.session_schemas import SessionSearchResultSnapshot


class SessionSearchResultSpec(msgspec.Struct, kw_only=True):
    """Represents one decoded session-search result item before normalization."""

    session_id: object = None
    timestamp: object = None
    cwd: object = None
    record_type: object = None
    line_number: object = None
    snippet: object = None


class SessionSearchSpec(msgspec.Struct, kw_only=True):
    """Represents the decoded session-search transport payload."""

    query: object = None
    searched_files: object = None
    matched_sessions: object = None
    results: object = None


class SessionSearchTransportResultPayload(TypedDict):
    """Represents the stable observed subset for one session-search result item."""

    session_id: str
    timestamp: str
    cwd: str
    record_type: str
    line_number: int
    snippet: str


type SessionSearchTransportResults = list[SessionSearchTransportResultPayload] | list[object]
type SessionSearchNormalizedResults = list[SessionSearchResultSnapshot] | list[object]


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
