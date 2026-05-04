from typing import Required, TypedDict


class SessionSearchTransportResultPayload(TypedDict):
    """Represents the stable observed subset for one session-search result item."""

    session_id: Required[str]
    timestamp: Required[str]
    cwd: Required[str]
    record_type: Required[str]
    line_number: Required[int]
    snippet: Required[str]


class SessionSearchTransportPayload(TypedDict):
    """Represents the stable top-level transport subset for session search."""

    query: Required[str]
    searched_files: Required[int]
    matched_sessions: Required[int]
    results: Required[list[SessionSearchTransportResultPayload] | list[object]]


class SessionSearchNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for session search."""

    query: Required[str]
    searched_files: Required[int]
    matched_sessions: Required[int]
    results: Required[list[SessionSearchTransportResultPayload] | list[object]]
