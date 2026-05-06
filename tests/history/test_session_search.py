import asyncio
import inspect

import pytest
from pydantic import ValidationError

from omx_remote.history import session_search
from omx_remote.schemas.history_schemas import SessionSearchRequest
from omx_remote.shared.exceptions import HistorySurfaceError


class DummyResult:
    def __init__(self, stdout: str = "{}", stderr: str = "") -> None:
        self.stdout = stdout
        self.stderr = stderr


def test_search_sessions_is_async() -> None:
    assert inspect.iscoroutinefunction(session_search.search_sessions)


def test_search_sessions_accepts_typed_request() -> None:
    coroutine = session_search.search_sessions(SessionSearchRequest(query="hermes"))

    assert inspect.isawaitable(coroutine)
    asyncio.run(coroutine)


def test_search_sessions_returns_zero_result_snapshot(monkeypatch) -> None:
    monkeypatch.setattr(
        session_search,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"query":"hermes","searched_files":0,"matched_sessions":0,"results":[]}\n'
        ),
    )

    result = asyncio.run(session_search.search_sessions(SessionSearchRequest(query="hermes")))

    assert result.query == "hermes"
    assert result.matched_sessions == 0
    assert result.results == ()


def test_search_sessions_returns_populated_snapshot(monkeypatch) -> None:
    monkeypatch.setattr(
        session_search,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"query":"hermes","searched_files":1,"matched_sessions":1,"results":[{"session_id":"019de86e-6ec0-7993-8d67-23d629f5783c","timestamp":"2026-05-02T11:24:04.685Z","cwd":"/tmp/project","transcript_path":"/tmp/file.jsonl","transcript_path_relative":"sessions/file.jsonl","record_type":"event_msg:exec_command_end","line_number":26,"snippet":"probe result"}]}\n'
        ),
    )

    result = asyncio.run(session_search.search_sessions(SessionSearchRequest(query="hermes")))

    assert result.matched_sessions == 1
    assert isinstance(result.results, tuple)
    assert result.results[0].session_id == "019de86e-6ec0-7993-8d67-23d629f5783c"
    assert result.results[0].snippet == "probe result"


def test_search_sessions_rejects_unparseable_json_transport(monkeypatch) -> None:
    monkeypatch.setattr(
        session_search,
        "run_omx_command",
        lambda arguments: DummyResult(stdout="not-json\n"),
    )

    with pytest.raises(HistorySurfaceError):
        asyncio.run(session_search.search_sessions(SessionSearchRequest(query="hermes")))


def test_search_sessions_rejects_missing_searched_files_field(monkeypatch) -> None:
    monkeypatch.setattr(
        session_search,
        "run_omx_command",
        lambda arguments: DummyResult(stdout='{"query":"hermes"}\n'),
    )

    with pytest.raises(HistorySurfaceError):
        asyncio.run(session_search.search_sessions(SessionSearchRequest(query="hermes")))


def test_search_sessions_rejects_non_mapping_result_items(monkeypatch) -> None:
    monkeypatch.setattr(
        session_search,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"query":"hermes","searched_files":1,"matched_sessions":1,"results":["bad-entry"]}\n'
        ),
    )

    with pytest.raises(ValidationError):
        asyncio.run(session_search.search_sessions(SessionSearchRequest(query="hermes")))


def test_load_session_search_transport_payload_rejects_non_object_transport() -> None:
    with pytest.raises(HistorySurfaceError):
        session_search._load_session_search_transport_payload("[]")
