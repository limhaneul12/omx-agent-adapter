from typing import get_type_hints

from omx_remote.adapter_types.history_types import (
    SessionSearchNormalizedPayload,
    SessionSearchResultSpec,
    SessionSearchSpec,
    SessionSearchTransportPayload,
    SessionSearchTransportResultPayload,
)


def test_session_search_msgspec_specs_use_nullable_stable_fields() -> None:
    result_hints = get_type_hints(SessionSearchResultSpec)
    payload_hints = get_type_hints(SessionSearchSpec)

    assert result_hints == {
        "session_id": str | None,
        "timestamp": str | None,
        "cwd": str | None,
        "record_type": str | None,
        "line_number": int | None,
        "snippet": str | None,
    }
    assert payload_hints == {
        "query": str | None,
        "searched_files": int | None,
        "matched_sessions": int | None,
        "results": list[SessionSearchResultSpec] | None,
    }


def test_session_search_typed_dicts_accept_narrowed_stable_shapes() -> None:
    result_payload: SessionSearchTransportResultPayload = {
        "session_id": "019df206-3b0d-7520-9a99-d1526d390903",
        "timestamp": "2026-05-04T08:06:27.971Z",
        "cwd": "/Users/imhaneul/Documents/sky_document/project/trandai-informat-fommo",
        "record_type": "compacted",
        "line_number": 300,
        "snippet": "probe result",
    }
    transport_payload: SessionSearchTransportPayload = {
        "query": "hermes",
        "searched_files": 7,
        "matched_sessions": 2,
        "results": [result_payload],
    }
    normalized_payload: SessionSearchNormalizedPayload = {
        "query": "hermes",
        "searched_files": 7,
        "matched_sessions": 2,
        "results": [result_payload],
    }

    assert transport_payload["query"] == "hermes"
    assert transport_payload["searched_files"] == 7
    assert transport_payload["matched_sessions"] == 2
    assert transport_payload["results"][0]["line_number"] == 300
    assert normalized_payload["results"][0]["record_type"] == "compacted"
