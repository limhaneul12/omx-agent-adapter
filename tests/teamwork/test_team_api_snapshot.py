import asyncio
import inspect

import pytest
from pydantic import ValidationError

from omx_remote.schemas.teamwork_schemas import (
    TeamApiListTasksRequest,
    TeamApiReadEventsRequest,
)
from omx_remote.shared.exceptions.teamwork_exceptions import TeamworkSurfaceError
from omx_remote.teamwork import team_api_snapshot


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


def test_read_team_api_list_tasks_normalizes_live_task_payload_shape(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","ok":true,"data":{"count":1,"tasks":[{"subject":"Team surface closure: status/await and team-api regressions","description":"Own src/teamwork/team_snapshot.py","status":"in_progress","owner":"worker-1","depends_on":[],"role":"executor","id":"1","version":3,"created_at":"2026-05-03T04:17:53.343Z","claim":{"owner":"worker-1","token":"claim-token","leased_until":"2026-05-03T04:33:35.285Z"},"requires_code_change":true}]}}\n'
        ),
    )

    result = asyncio.run(
        team_api_snapshot.read_team_api_list_tasks(
            TeamApiListTasksRequest(team_name="roadmap-closure-burnd-0cc0315d")
        )
    )

    assert result.count == 1
    assert result.tasks[0].id == "1"
    assert (
        result.tasks[0].subject
        == "Team surface closure: status/await and team-api regressions"
    )
    assert result.tasks[0].status == "in_progress"
    assert result.tasks[0].owner == "worker-1"


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


def test_read_team_api_read_events_normalizes_live_event_payload_shape(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","ok":true,"data":{"count":2,"cursor":"cursor-1","events":[{"type":"message_received","worker":"leader-fixed","message_id":"message-1","event_id":"event-1","team":"roadmap-closure-burnd-0cc0315d","created_at":"2026-05-03T04:18:19.286Z"},{"type":"task_completed","worker":"worker-3","task_id":"4","message_id":null,"event_id":"event-2","team":"roadmap-closure-burnd-0cc0315d","created_at":"2026-05-03T04:21:34.354Z"}]}}\n'
        ),
    )

    result = asyncio.run(
        team_api_snapshot.read_team_api_read_events(
            TeamApiReadEventsRequest(team_name="roadmap-closure-burnd-0cc0315d")
        )
    )

    assert result.count == 2
    assert result.cursor == "cursor-1"
    assert result.events[0].type == "message_received"
    assert result.events[0].worker == "leader-fixed"
    assert result.events[0].message_id == "message-1"
    assert result.events[0].task_id is None
    assert result.events[1].type == "task_completed"
    assert result.events[1].worker == "worker-3"
    assert result.events[1].task_id == "4"


def test_load_team_api_payload_rejects_non_object_data_payload() -> None:
    with pytest.raises(TeamworkSurfaceError):
        team_api_snapshot._load_team_api_payload(
            '{"ok":true,"data":[]}',
            "omx team api list-tasks",
        )
