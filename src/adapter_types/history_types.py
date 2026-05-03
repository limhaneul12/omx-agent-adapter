from typing import Required, TypedDict


class SessionSearchTransportResultPayload(TypedDict):
    session_id: Required[object]
    timestamp: Required[object]
    cwd: Required[object]
    record_type: Required[object]
    line_number: Required[object]
    snippet: Required[object]


class SessionSearchTransportPayload(TypedDict):
    query: Required[object]
    searched_files: Required[object]
    matched_sessions: Required[object]
    results: Required[object]


class SessionSearchNormalizedPayload(TypedDict):
    query: Required[object]
    searched_files: Required[object]
    matched_sessions: Required[object]
    results: Required[object]
