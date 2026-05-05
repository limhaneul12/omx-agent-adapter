from typing import TypedDict


class SessionSearchTransportResultPayload(TypedDict):
    """Represents the stable observed subset for one session-search result item."""

    session_id: str
    timestamp: str
    cwd: str
    record_type: str
    line_number: int
    snippet: str


class SessionSearchTransportPayload(TypedDict):
    """Represents the stable top-level transport subset for session search."""

    query: str
    searched_files: int
    matched_sessions: int
    results: list[SessionSearchTransportResultPayload] | list[object]


class SessionSearchNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for session search."""

    query: str
    searched_files: int
    matched_sessions: int
    results: list[SessionSearchTransportResultPayload] | list[object]
