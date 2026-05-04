import pytest
from pydantic import ValidationError

from omx_remote.schemas.teamwork_schemas import (
    TeamApiMailboxListRequest,
    TeamApiMailboxListSnapshot,
    TeamApiListTasksRequest,
    TeamApiListTasksSnapshot,
    TeamApiReadEventsRequest,
    TeamApiReadEventsSnapshot,
    TeamApiReadMonitorSnapshotRequest,
    TeamApiReadMonitorSnapshot,
    TeamApiReadWorkerStatusRequest,
    TeamApiWorkerStatusSnapshot,
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


def test_team_api_list_tasks_snapshot_accepts_normalized_live_task_shape() -> None:
    result = TeamApiListTasksSnapshot.model_validate(
        {
            "count": 1,
            "tasks": [
                {
                    "id": "1",
                    "subject": "Team surface closure",
                    "status": "in_progress",
                    "owner": "worker-1",
                }
            ],
        }
    )

    assert result.tasks[0].subject == "Team surface closure"
    assert result.tasks[0].owner == "worker-1"


def test_team_api_read_events_request_accepts_required_team_name() -> None:
    result = TeamApiReadEventsRequest.model_validate({"team_name": "alpha"})

    assert result.team_name == "alpha"


def test_team_api_read_monitor_snapshot_request_accepts_required_team_name() -> None:
    result = TeamApiReadMonitorSnapshotRequest.model_validate({"team_name": "alpha"})

    assert result.team_name == "alpha"


def test_team_api_read_monitor_snapshot_request_rejects_empty_team_name() -> None:
    with pytest.raises(ValidationError):
        TeamApiReadMonitorSnapshotRequest.model_validate({"team_name": ""})


def test_team_api_read_monitor_snapshot_accepts_null_snapshot() -> None:
    result = TeamApiReadMonitorSnapshot.model_validate({"snapshot": None})

    assert result.snapshot is None


def test_team_api_read_monitor_snapshot_rejects_unexpected_extra_fields() -> None:
    with pytest.raises(ValidationError):
        TeamApiReadMonitorSnapshot.model_validate(
            {"snapshot": None, "unexpected": True}
        )


def test_team_api_read_events_request_rejects_empty_team_name() -> None:
    with pytest.raises(ValidationError):
        TeamApiReadEventsRequest.model_validate({"team_name": ""})


def test_team_api_mailbox_list_request_accepts_required_fields() -> None:
    result = TeamApiMailboxListRequest.model_validate(
        {"team_name": "alpha", "worker": "worker-1"}
    )

    assert result.team_name == "alpha"
    assert result.worker == "worker-1"


def test_team_api_mailbox_list_request_rejects_empty_worker() -> None:
    with pytest.raises(ValidationError):
        TeamApiMailboxListRequest.model_validate(
            {"team_name": "alpha", "worker": ""}
        )


def test_team_api_read_worker_status_request_accepts_required_fields() -> None:
    result = TeamApiReadWorkerStatusRequest.model_validate(
        {"team_name": "alpha", "worker": "worker-1"}
    )

    assert result.team_name == "alpha"
    assert result.worker == "worker-1"


def test_team_api_worker_status_snapshot_accepts_live_shape() -> None:
    result = TeamApiWorkerStatusSnapshot.model_validate(
        {
            "worker": "worker-1",
            "state": "unknown",
            "updated_at": "1970-01-01T00:00:00.000Z",
        }
    )

    assert result.worker == "worker-1"
    assert result.state == "unknown"


def test_team_api_mailbox_list_snapshot_accepts_empty_message_list() -> None:
    result = TeamApiMailboxListSnapshot.model_validate(
        {"worker": "worker-1", "count": 0, "messages": []}
    )

    assert result.worker == "worker-1"
    assert result.count == 0
    assert result.messages == []


def test_team_api_mailbox_list_snapshot_rejects_unexpected_extra_fields() -> None:
    with pytest.raises(ValidationError):
        TeamApiMailboxListSnapshot.model_validate(
            {
                "worker": "worker-1",
                "count": 0,
                "messages": [],
                "unexpected": True,
            }
        )


def test_team_api_mailbox_list_snapshot_accepts_normalized_live_message_shape() -> None:
    result = TeamApiMailboxListSnapshot.model_validate(
        {
            "worker": "worker-1",
            "count": 1,
            "messages": [
                {
                    "id": "message-1",
                    "subject": "follow-up",
                    "body": "please re-run tests",
                    "delivered": False,
                }
            ],
        }
    )

    assert result.messages[0].id == "message-1"
    assert result.messages[0].delivered is False


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


def test_team_api_read_events_snapshot_accepts_normalized_live_event_shape() -> None:
    result = TeamApiReadEventsSnapshot.model_validate(
        {
            "count": 1,
            "cursor": "cursor-1",
            "events": [
                {
                    "type": "message_received",
                    "worker": "leader-fixed",
                    "message_id": "message-1",
                }
            ],
        }
    )

    assert result.events[0].type == "message_received"
    assert result.events[0].message_id == "message-1"
