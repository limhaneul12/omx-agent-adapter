from omx_remote.history.session_search import _normalize_session_search_results
from omx_remote.schemas.history_session_schemas import SessionSearchResultSnapshot


def test_history_type_aliases_cover_result_lists() -> None:
    from omx_remote.adapter_types.history_types import (
        SessionSearchNormalizedResults,
        SessionSearchTransportResults,
    )

    assert SessionSearchTransportResults is not None
    assert SessionSearchNormalizedResults is not None


def test_session_search_normalizes_result_items_as_pydantic_models() -> None:
    result_items = _normalize_session_search_results(
        [
            {
                "session_id": "s1",
                "timestamp": "2026-05-06T00:00:00Z",
                "cwd": "/tmp/project",
                "record_type": "message",
                "line_number": 7,
                "snippet": "hello",
            }
        ]
    )

    assert isinstance(result_items[0], SessionSearchResultSnapshot)
    assert result_items[0].session_id == "s1"
