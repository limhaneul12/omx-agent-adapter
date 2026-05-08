import asyncio

import msgspec
import orjson

from omx_remote.adapter_types.history_types import (
    SessionSearchNormalizedPayload,
    SessionSearchNormalizedResults,
    SessionSearchResultSpec,
    SessionSearchSpec,
    SessionSearchTransportPayload,
    SessionSearchTransportResultPayload,
    SessionSearchTransportResults,
)
from omx_remote.execution.invoke import run_omx_command
from omx_remote.schemas.history.session_schemas import (
    SessionSearchRequest,
    SessionSearchResultSnapshot,
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
    """Loads one session-search transport payload from raw stdout.
    
    Args:
        stdout [str]: Function argument.
    
    Returns:
        SessionSearchTransportPayload: Function return value.
    """
    if not stdout:
        raise HistorySurfaceError("omx session search returned no stdout output")

    try:
        decoded_payload: object = orjson.loads(stdout)
        parsed_payload: SessionSearchSpec = msgspec.convert(
            decoded_payload,
            type=SessionSearchSpec,
        )
    except (orjson.JSONDecodeError, msgspec.ValidationError) as error:
        raise HistorySurfaceError(
            "omx session search returned unparseable JSON output"
        ) from error

    if not isinstance(decoded_payload, dict):
        raise HistorySurfaceError("omx session search returned a non-object JSON payload")
    if not isinstance(parsed_payload.query, str):
        raise HistorySurfaceError("omx session search returned a non-string query")
    if not isinstance(parsed_payload.searched_files, int):
        raise HistorySurfaceError(
            "omx session search returned a non-integer searched_files"
        )
    if not isinstance(parsed_payload.matched_sessions, int):
        raise HistorySurfaceError(
            "omx session search returned a non-integer matched_sessions"
        )
    if not isinstance(parsed_payload.results, list):
        raise HistorySurfaceError("omx session search returned a non-list results payload")

    result = SessionSearchTransportPayload(
        query=parsed_payload.query,
        searched_files=parsed_payload.searched_files,
        matched_sessions=parsed_payload.matched_sessions,
        results=parsed_payload.results,
    )
    return result

def _normalize_session_search(stdout: str) -> SessionSearchSnapshot:
    """Normalizes one `omx session search ... --json` payload.
    
    Args:
        stdout [str]: Function argument.
    
    Returns:
        SessionSearchSnapshot: Function return value.
    """
    parsed_payload: SessionSearchTransportPayload = _load_session_search_transport_payload(
        stdout
    )

    raw_results: SessionSearchTransportResults = parsed_payload["results"]
    normalized_results: SessionSearchNormalizedResults = _normalize_session_search_results(
        raw_results
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
    raw_results: SessionSearchTransportResults,
) -> SessionSearchNormalizedResults:
    """Normalizes result-item objects into pydantic session-search snapshots.

    Args:
        raw_results [SessionSearchTransportResults]: Raw result list read from the session-search transport payload.

    Returns:
        SessionSearchNormalizedResults: Result list promoted to pydantic snapshots.
    """
    normalized_results: list[SessionSearchResultSnapshot] = []
    for result_item in raw_results:
        normalized_result_payload = _session_search_result_payload_from_item(
            result_item
        )
        normalized_result_item: SessionSearchResultSnapshot = (
            SessionSearchResultSnapshot.model_validate(normalized_result_payload)
        )
        normalized_results.append(normalized_result_item)

    return normalized_results


def _session_search_result_payload_from_item(
    result_item: SessionSearchResultSpec | SessionSearchTransportResultPayload,
) -> SessionSearchTransportResultPayload:
    """Converts one loaded or direct-test result item into the stable payload shape.

    Args:
        result_item [SessionSearchResultSpec | SessionSearchTransportResultPayload]: Loaded msgspec item or already materialized stable payload.

    Returns:
        SessionSearchTransportResultPayload: Stable result payload for final schema validation.
    """
    if isinstance(result_item, SessionSearchResultSpec):
        return SessionSearchTransportResultPayload(
            session_id=result_item.session_id,
            timestamp=result_item.timestamp,
            cwd=result_item.cwd,
            record_type=result_item.record_type,
            line_number=result_item.line_number,
            snippet=result_item.snippet,
        )

    return SessionSearchTransportResultPayload(
        session_id=result_item["session_id"],
        timestamp=result_item["timestamp"],
        cwd=result_item["cwd"],
        record_type=result_item["record_type"],
        line_number=result_item["line_number"],
        snippet=result_item["snippet"],
    )
