from typing import TypedDict


class SessionSearchTransportResultPayload(TypedDict):
    session_id: object
    timestamp: object
    cwd: object
    record_type: object
    line_number: object
    snippet: object


class SessionSearchTransportPayload(TypedDict):
    query: object
    searched_files: object
    matched_sessions: object
    results: object


class SessionSearchNormalizedPayload(TypedDict):
    query: object
    searched_files: object
    matched_sessions: object
    results: object
