import asyncio

import pytest

from omx_remote.schemas.teamwork.api_request_schemas import TeamApiReadEventsRequest
from omx_remote.shared.exceptions import TeamworkSurfaceError
from omx_remote.teamwork import team_api_snapshot


class DummyResult:
    def __init__(self, stdout: str = "{}", stderr: str = "") -> None:
        self.stdout = stdout
        self.stderr = stderr


def test_read_team_api_read_events_preserves_null_message_id_from_live_payload(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","ok":true,"data":{"count":1,"cursor":"cursor-1","events":[{"type":"task_completed","worker":"worker-3","task_id":"4","message_id":null,"event_id":"event-2"}]}}\n'
        ),
    )

    result = asyncio.run(
        team_api_snapshot.read_team_api_read_events(
            TeamApiReadEventsRequest(team_name="roadmap-closure-burnd-0cc0315d")
        )
    )

    assert result.count == 1
    assert result.events[0].type == "task_completed"
    assert result.events[0].worker == "worker-3"
    assert result.events[0].task_id == "4"
    assert result.events[0].message_id is None


def test_read_team_api_read_events_rejects_non_object_event_payload_item(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","ok":true,"data":{"count":1,"cursor":"cursor-1","events":["not-an-event"]}}\n'
        ),
    )

    with pytest.raises(TeamworkSurfaceError):
        asyncio.run(
            team_api_snapshot.read_team_api_read_events(
                TeamApiReadEventsRequest(team_name="alpha")
            )
        )


def test_read_team_api_read_events_rejects_null_event_payload_item(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","ok":true,"data":{"count":1,"cursor":"cursor-1","events":[null]}}\n'
        ),
    )

    with pytest.raises(TeamworkSurfaceError):
        asyncio.run(
            team_api_snapshot.read_team_api_read_events(
                TeamApiReadEventsRequest(team_name="alpha")
            )
        )
