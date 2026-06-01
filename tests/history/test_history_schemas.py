import pytest
from pydantic import ValidationError

from omx_remote.schemas.history_session_schemas import (
    SessionSearchRequest,
    SessionSearchResultSnapshot,
    SessionSearchSnapshot,
)


def test_session_search_request_accepts_query() -> None:
    result = SessionSearchRequest.model_validate({"query": "hermes"})

    assert result.query == "hermes"
    assert result.limit is None


def test_session_search_request_accepts_optional_limit() -> None:
    result = SessionSearchRequest.model_validate({"query": "hermes", "limit": 5})

    assert result.limit == 5


def test_session_search_request_rejects_empty_query() -> None:
    with pytest.raises(ValidationError):
        SessionSearchRequest.model_validate({"query": ""})


def test_session_search_request_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        SessionSearchRequest.model_validate({"query": "hermes", "unexpected": True})


def test_session_search_result_snapshot_accepts_minimal_result() -> None:
    result = SessionSearchResultSnapshot.model_validate(
        {
            "session_id": "019de86e-6ec0-7993-8d67-23d629f5783c",
            "timestamp": "2026-05-02T11:24:04.685Z",
            "cwd": "/tmp/project",
            "record_type": "event_msg:exec_command_end",
            "line_number": 26,
            "snippet": "probe result",
        }
    )

    assert result.session_id == "019de86e-6ec0-7993-8d67-23d629f5783c"
    assert result.line_number == 26


def test_session_search_snapshot_accepts_zero_results() -> None:
    result = SessionSearchSnapshot.model_validate(
        {"query": "hermes", "searched_files": 0, "matched_sessions": 0, "results": []}
    )

    assert result.query == "hermes"
    assert result.results == ()


def test_session_search_snapshot_accepts_populated_results() -> None:
    result = SessionSearchSnapshot.model_validate(
        {
            "query": "hermes",
            "searched_files": 1,
            "matched_sessions": 1,
            "results": [
                {
                    "session_id": "019de86e-6ec0-7993-8d67-23d629f5783c",
                    "timestamp": "2026-05-02T11:24:04.685Z",
                    "cwd": "/tmp/project",
                    "record_type": "event_msg:exec_command_end",
                    "line_number": 26,
                    "snippet": "probe result",
                }
            ],
        }
    )

    assert result.matched_sessions == 1
    assert isinstance(result.results, tuple)
    assert len(result.results) == 1


def test_session_search_snapshot_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        SessionSearchSnapshot.model_validate(
            {
                "query": "hermes",
                "searched_files": 0,
                "matched_sessions": 0,
                "results": [],
                "unexpected": True,
            }
        )
