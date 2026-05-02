import pytest
from pydantic import ValidationError

from schemas.teamwork_schemas import (
    TeamApiListTasksRequest,
    TeamApiListTasksSnapshot,
    TeamApiReadEventsRequest,
    TeamApiReadEventsSnapshot,
)


def test_team_api_list_tasks_request_accepts_required_team_name() -> None:
    result = TeamApiListTasksRequest.model_validate({"team_name": "alpha"})

    assert result.team_name == "alpha"


def test_team_api_list_tasks_request_rejects_empty_team_name() -> None:
    with pytest.raises(ValidationError):
        TeamApiListTasksRequest.model_validate({"team_name": ""})


def test_team_api_list_tasks_snapshot_accepts_empty_task_list() -> None:
    result = TeamApiListTasksSnapshot.model_validate(
        {"count": 0, "tasks": []}
    )

    assert result.count == 0
    assert result.tasks == []


def test_team_api_list_tasks_snapshot_rejects_unexpected_extra_fields() -> None:
    with pytest.raises(ValidationError):
        TeamApiListTasksSnapshot.model_validate(
            {"count": 0, "tasks": [], "unexpected": True}
        )


def test_team_api_read_events_request_accepts_required_team_name() -> None:
    result = TeamApiReadEventsRequest.model_validate({"team_name": "alpha"})

    assert result.team_name == "alpha"


def test_team_api_read_events_request_rejects_empty_team_name() -> None:
    with pytest.raises(ValidationError):
        TeamApiReadEventsRequest.model_validate({"team_name": ""})


def test_team_api_read_events_snapshot_accepts_empty_event_list() -> None:
    result = TeamApiReadEventsSnapshot.model_validate(
        {"count": 0, "cursor": "", "events": []}
    )

    assert result.count == 0
    assert result.cursor == ""
    assert result.events == []


def test_team_api_read_events_snapshot_rejects_unexpected_extra_fields() -> None:
    with pytest.raises(ValidationError):
        TeamApiReadEventsSnapshot.model_validate(
            {"count": 0, "cursor": "", "events": [], "unexpected": True}
        )
