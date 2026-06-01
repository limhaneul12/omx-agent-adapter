import asyncio
from unittest.mock import Mock, patch

import pytest

from omx_remote.schemas.teamwork.api_request_schemas import (
    TeamApiListTasksRequest,
    TeamApiReadEventsRequest,
)
from omx_remote.shared.exceptions import TeamworkSurfaceError
from omx_remote.teamwork.team_api_snapshot import (
    read_team_api_list_tasks,
    read_team_api_read_events,
)


@patch("omx_remote.teamwork.team_api_snapshot.run_omx_command")
def test_read_team_api_list_tasks_rejects_count_mismatch(
    mock_run_omx_command: Mock,
) -> None:
    mock_run_omx_command.return_value = Mock(
        returncode=0,
        stdout='{"schema_version":"1.0","ok":true,"data":{"count":2,"tasks":[{"id":"1","subject":"Only task","status":"in_progress","owner":"worker-1"}]}}\n',
        stderr="",
    )

    with pytest.raises(
        TeamworkSurfaceError,
        match=r"omx team api list-tasks returned count that does not match tasks length",
    ):
        asyncio.run(
            read_team_api_list_tasks(TeamApiListTasksRequest(team_name="alpha"))
        )


@patch("omx_remote.teamwork.team_api_snapshot.run_omx_command")
def test_read_team_api_read_events_rejects_count_mismatch(
    mock_run_omx_command: Mock,
) -> None:
    mock_run_omx_command.return_value = Mock(
        returncode=0,
        stdout='{"schema_version":"1.0","ok":true,"data":{"count":2,"cursor":"cursor-1","events":[{"type":"message_received","worker":"worker-1","message_id":"message-1"}]}}\n',
        stderr="",
    )

    with pytest.raises(
        TeamworkSurfaceError,
        match=r"omx team api read-events returned count that does not match events length",
    ):
        asyncio.run(
            read_team_api_read_events(TeamApiReadEventsRequest(team_name="alpha"))
        )
