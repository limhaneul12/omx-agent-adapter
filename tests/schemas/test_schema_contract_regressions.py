import pytest
from pydantic import ValidationError

from omx_remote.schemas.bridge_schemas import AdapterCapabilitySnapshot
from omx_remote.schemas.history_schemas import SessionSearchResultSnapshot
from omx_remote.schemas.teamwork_schemas import TeamApiEventSnapshot, TeamApiTaskSnapshot


def test_adapter_capability_snapshot_rejects_empty_required_fields() -> None:
    with pytest.raises(ValidationError):
        AdapterCapabilitySnapshot.model_validate(
            {"id": "", "label": "x", "status": "ready", "summary": "ok"}
        )


def test_session_search_result_snapshot_rejects_empty_snippet() -> None:
    with pytest.raises(ValidationError):
        SessionSearchResultSnapshot.model_validate(
            {
                "session_id": "session-1",
                "timestamp": "2026-05-02T11:24:04.685Z",
                "cwd": "/tmp/project",
                "record_type": "event_msg:exec_command_end",
                "line_number": 26,
                "snippet": "",
            }
        )


def test_team_api_task_snapshot_rejects_empty_subject() -> None:
    with pytest.raises(ValidationError):
        TeamApiTaskSnapshot.model_validate(
            {"id": "1", "subject": "", "status": "in_progress", "owner": "worker-1"}
        )


def test_team_api_event_snapshot_accepts_null_message_id() -> None:
    result = TeamApiEventSnapshot.model_validate(
        {
            "type": "task_completed",
            "worker": "worker-3",
            "task_id": "4",
            "message_id": None,
        }
    )

    assert result.message_id is None
