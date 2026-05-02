import asyncio
import inspect

import pytest
from pydantic import ValidationError

from schemas.teamwork_schemas import (
    TeamApiListTasksRequest,
    TeamApiReadEventsRequest,
)
from shared.exceptions.teamwork_exceptions import TeamworkSurfaceError
from teamwork import team_api_snapshot


class DummyResult:
    def __init__(self, stdout: str = "{}", stderr: str = "") -> None:
        self.stdout = stdout
        self.stderr = stderr


def test_read_team_api_list_tasks_is_async() -> None:
    assert inspect.iscoroutinefunction(team_api_snapshot.read_team_api_list_tasks)


def test_read_team_api_list_tasks_accepts_typed_request() -> None:
    coroutine = team_api_snapshot.read_team_api_list_tasks(
        TeamApiListTasksRequest(team_name="alpha")
    )

    assert inspect.isawaitable(coroutine)
    asyncio.run(coroutine)


def test_read_team_api_list_tasks_returns_empty_snapshot(monkeypatch) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","timestamp":"2026-05-02T14:20:07.659Z","command":"omx team api list-tasks","ok":true,"operation":"list-tasks","data":{"count":0,"tasks":[]}}\n'
        ),
    )

    result = asyncio.run(
        team_api_snapshot.read_team_api_list_tasks(
            TeamApiListTasksRequest(team_name="missing-team")
        )
    )

    assert result.count == 0
    assert result.tasks == []


def test_read_team_api_list_tasks_rejects_unparseable_json_transport(monkeypatch) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(stdout="not-json\n"),
    )

    with pytest.raises(TeamworkSurfaceError):
        asyncio.run(
            team_api_snapshot.read_team_api_list_tasks(
                TeamApiListTasksRequest(team_name="alpha")
            )
        )


def test_read_team_api_list_tasks_preserves_required_contract_validation(monkeypatch) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","ok":true,"data":{}}\n'
        ),
    )

    with pytest.raises(ValidationError):
        asyncio.run(
            team_api_snapshot.read_team_api_list_tasks(
                TeamApiListTasksRequest(team_name="alpha")
            )
        )


def test_read_team_api_read_events_is_async() -> None:
    assert inspect.iscoroutinefunction(team_api_snapshot.read_team_api_read_events)


def test_read_team_api_read_events_accepts_typed_request() -> None:
    coroutine = team_api_snapshot.read_team_api_read_events(
        TeamApiReadEventsRequest(team_name="alpha")
    )

    assert inspect.isawaitable(coroutine)
    asyncio.run(coroutine)


def test_read_team_api_read_events_returns_empty_snapshot(monkeypatch) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","timestamp":"2026-05-02T14:20:08.980Z","command":"omx team api read-events","ok":true,"operation":"read-events","data":{"count":0,"cursor":"","events":[]}}\n'
        ),
    )

    result = asyncio.run(
        team_api_snapshot.read_team_api_read_events(
            TeamApiReadEventsRequest(team_name="missing-team")
        )
    )

    assert result.count == 0
    assert result.cursor == ""
    assert result.events == []


def test_read_team_api_read_events_rejects_transport_error_payload(monkeypatch) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","ok":false,"error":{"code":"team_not_found","message":"team_not_found"}}\n'
        ),
    )

    with pytest.raises(TeamworkSurfaceError):
        asyncio.run(
            team_api_snapshot.read_team_api_read_events(
                TeamApiReadEventsRequest(team_name="missing-team")
            )
        )
