import asyncio

import orjson

from adapter_types.history_types import (
    SessionSearchNormalizedPayload,
    SessionSearchTransportPayload,
    SessionSearchTransportResultPayload,
)
from execution.invoke import run_omx_command
from schemas.history_schemas import SessionSearchRequest, SessionSearchSnapshot
from shared.exceptions.history_exceptions import HistorySurfaceError


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

    result: SessionSearchTransportPayload = {
        "query": parsed_payload.get("query"),
        "searched_files": parsed_payload.get("searched_files"),
        "matched_sessions": parsed_payload.get("matched_sessions"),
        "results": parsed_payload.get("results"),
    }
    return result


def _normalize_session_search(stdout: str) -> SessionSearchSnapshot:
    """Normalizes one `omx session search ... --json` payload."""
    parsed_payload: SessionSearchTransportPayload = _load_session_search_transport_payload(
        stdout
    )

    raw_results: object | None = parsed_payload.get("results")
    normalized_results: object = _normalize_session_search_results(raw_results)

    normalized_payload: SessionSearchNormalizedPayload = {
        "query": parsed_payload.get("query"),
        "searched_files": parsed_payload.get("searched_files"),
        "matched_sessions": parsed_payload.get("matched_sessions"),
        "results": normalized_results,
    }
    result: SessionSearchSnapshot = SessionSearchSnapshot.model_validate(
        normalized_payload
    )
    return result


def _normalize_session_search_results(raw_results: object) -> object:
    """Preserves result-item validation rather than silently dropping malformed data."""
    if not isinstance(raw_results, list):
        return raw_results

    normalized_results: list[object] = []
    result_item: object
    for result_item in raw_results:
        if not isinstance(result_item, dict):
            normalized_results.append(result_item)
            continue
        normalized_result_item: SessionSearchTransportResultPayload = {
            "session_id": result_item.get("session_id"),
            "timestamp": result_item.get("timestamp"),
            "cwd": result_item.get("cwd"),
            "record_type": result_item.get("record_type"),
            "line_number": result_item.get("line_number"),
            "snippet": result_item.get("snippet"),
        }
        normalized_results.append(normalized_result_item)
    return normalized_results
