from typing import Required, TypedDict


class SessionSearchTransportResultPayload(TypedDict):
    session_id: Required[str]
    timestamp: Required[str]
    cwd: Required[str]
    record_type: Required[str]
    line_number: Required[int]
    snippet: Required[str]


class SessionSearchTransportPayload(TypedDict):
    query: Required[str]
    searched_files: Required[int]
    matched_sessions: Required[int]
    results: Required[list[SessionSearchTransportResultPayload] | list[object]]


class SessionSearchNormalizedPayload(TypedDict):
    query: Required[str]
    searched_files: Required[int]
    matched_sessions: Required[int]
    results: Required[list[SessionSearchTransportResultPayload] | list[object]]
