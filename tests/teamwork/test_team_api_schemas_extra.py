import pytest
from pydantic import ValidationError

from omx_remote.schemas.teamwork_schemas import TeamApiReadEventsSnapshot


def test_team_api_read_events_snapshot_accepts_task_completed_event_without_message_id() -> (
    None
):
    result = TeamApiReadEventsSnapshot.model_validate(
        {
            "count": 1,
            "cursor": "cursor-1",
            "events": [
                {
                    "type": "task_completed",
                    "worker": "worker-3",
                    "task_id": "4",
                    "message_id": None,
                }
            ],
        }
    )

    assert result.events[0].type == "task_completed"
    assert result.events[0].worker == "worker-3"
    assert result.events[0].task_id == "4"
    assert result.events[0].message_id is None


def test_team_api_read_events_snapshot_rejects_non_object_event_items() -> None:
    with pytest.raises(ValidationError):
        TeamApiReadEventsSnapshot.model_validate(
            {
                "count": 1,
                "cursor": "cursor-1",
                "events": ["not-an-event"],
            }
        )
