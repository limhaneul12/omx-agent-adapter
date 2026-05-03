import asyncio

from execution.invoke import run_omx_command
from schemas.history_schemas import SessionSearchRequest, SessionSearchSnapshot
from shared.exceptions.history_exceptions import HistorySurfaceError
from shared.json_transport import load_json_object_stdout


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


def _normalize_session_search(stdout: str) -> SessionSearchSnapshot:
    """Normalizes one `omx session search ... --json` payload."""
    parsed_payload: dict[str, object] = load_json_object_stdout(
        stdout,
        command_name="omx session search",
        error_type=HistorySurfaceError,
    )

    raw_results: object | None = parsed_payload.get("results")
    normalized_results: object = _normalize_session_search_results(raw_results)

    normalized_payload: dict[str, object] = {
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
        normalized_results.append(
            {
                "session_id": result_item.get("session_id"),
                "timestamp": result_item.get("timestamp"),
                "cwd": result_item.get("cwd"),
                "record_type": result_item.get("record_type"),
                "line_number": result_item.get("line_number"),
                "snippet": result_item.get("snippet"),
            }
        )
    return normalized_results
