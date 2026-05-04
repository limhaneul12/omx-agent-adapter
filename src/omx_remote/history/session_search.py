import asyncio

import orjson

from omx_remote.adapter_types.history_types import (
    SessionSearchNormalizedPayload,
    SessionSearchTransportPayload,
    SessionSearchTransportResultPayload,
)
from omx_remote.execution.invoke import run_omx_command
from omx_remote.schemas.history_schemas import (
    SessionSearchRequest,
    SessionSearchSnapshot,
)
from omx_remote.shared.exceptions import HistorySurfaceError


async def search_sessions(request: SessionSearchRequest) -> SessionSearchSnapshot:
    """Reads one typed session-search surface.

    Args:
        request [SessionSearchRequest]: Typed request boundary for `omx session search ... --json`.

    Returns:
        SessionSearchSnapshot: Normalized session-search contract built from the live search payload.
    """
    command_arguments: list[str] = ["session", "search", request.query, "--json"]
    if request.limit is not None:
        command_arguments.extend(["--limit", str(request.limit)])

    command_result = await asyncio.to_thread(run_omx_command, command_arguments)
    stdout: str = command_result.stdout.strip()
    result: SessionSearchSnapshot = _normalize_session_search(stdout)
    return result


def _load_session_search_transport_payload(stdout: str) -> SessionSearchTransportPayload:
    """Loads one session-search transport payload from raw stdout."""
    if not stdout:
        raise HistorySurfaceError("omx session search returned no stdout output")

    try:
        parsed_payload: object = orjson.loads(stdout)
    except orjson.JSONDecodeError as error:
        raise HistorySurfaceError(
            "omx session search returned unparseable JSON output"
        ) from error

    if not isinstance(parsed_payload, dict):
        raise HistorySurfaceError("omx session search returned a non-object JSON payload")

    query_value: object | None = parsed_payload.get("query")
    if not isinstance(query_value, str):
        raise HistorySurfaceError("omx session search returned a non-string query")

    searched_files_value: object | None = parsed_payload.get("searched_files")
    if not isinstance(searched_files_value, int):
        raise HistorySurfaceError(
            "omx session search returned a non-integer searched_files"
        )

    matched_sessions_value: object | None = parsed_payload.get("matched_sessions")
    if not isinstance(matched_sessions_value, int):
        raise HistorySurfaceError(
            "omx session search returned a non-integer matched_sessions"
        )

    results_value: object | None = parsed_payload.get("results")
    if not isinstance(results_value, list):
        raise HistorySurfaceError("omx session search returned a non-list results payload")

    result = SessionSearchTransportPayload(
        query=query_value,
        searched_files=searched_files_value,
        matched_sessions=matched_sessions_value,
        results=results_value,
    )
    return result

def _normalize_session_search(stdout: str) -> SessionSearchSnapshot:
    """Normalizes one `omx session search ... --json` payload."""
    parsed_payload: SessionSearchTransportPayload = _load_session_search_transport_payload(
        stdout
    )

    raw_results: list[SessionSearchTransportResultPayload] | list[object] = parsed_payload[
        "results"
    ]
    normalized_results: list[SessionSearchTransportResultPayload] | list[object] = (
        _normalize_session_search_results(raw_results)
    )

    normalized_payload = SessionSearchNormalizedPayload(
        query=parsed_payload["query"],
        searched_files=parsed_payload["searched_files"],
        matched_sessions=parsed_payload["matched_sessions"],
        results=normalized_results,
    )
    result: SessionSearchSnapshot = SessionSearchSnapshot.model_validate(
        normalized_payload
    )
    return result


def _normalize_session_search_results(
    raw_results: list[SessionSearchTransportResultPayload] | list[object],
) -> list[SessionSearchTransportResultPayload] | list[object]:
    """Preserves result-item validation rather than silently dropping malformed data."""
    if not isinstance(raw_results, list):
        return raw_results

    normalized_results: list[object] = []
    result_item: object
    for result_item in raw_results:
        if not isinstance(result_item, dict):
            normalized_results.append(result_item)
            continue
        session_id_value: object | None = result_item.get("session_id")
        timestamp_value: object | None = result_item.get("timestamp")
        cwd_value: object | None = result_item.get("cwd")
        record_type_value: object | None = result_item.get("record_type")
        line_number_value: object | None = result_item.get("line_number")
        snippet_value: object | None = result_item.get("snippet")

        normalized_result_item: SessionSearchTransportResultPayload
        if (
            isinstance(session_id_value, str)
            and isinstance(timestamp_value, str)
            and isinstance(cwd_value, str)
            and isinstance(record_type_value, str)
            and isinstance(line_number_value, int)
            and isinstance(snippet_value, str)
        ):
            normalized_result_item = {
                "session_id": session_id_value,
                "timestamp": timestamp_value,
                "cwd": cwd_value,
                "record_type": record_type_value,
                "line_number": line_number_value,
                "snippet": snippet_value,
            }
            normalized_results.append(normalized_result_item)
            continue

        normalized_results.append(result_item)
    return normalized_results
