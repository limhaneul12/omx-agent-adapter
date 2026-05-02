import pytest
from pydantic import ValidationError

from schemas.teamwork_schemas import (
    TeamAwaitRequest,
    TeamAwaitSnapshot,
    TeamStatusRequest,
    TeamStatusSnapshot,
)


def test_team_status_request_accepts_required_team_name() -> None:
    result = TeamStatusRequest.model_validate({"team_name": "alpha"})

    assert result.team_name == "alpha"


def test_team_status_request_rejects_empty_team_name() -> None:
    with pytest.raises(ValidationError):
        TeamStatusRequest.model_validate({"team_name": ""})


def test_team_status_request_rejects_unexpected_extra_fields() -> None:
    with pytest.raises(ValidationError):
        TeamStatusRequest.model_validate({"team_name": "alpha", "unexpected": True})


def test_team_await_request_accepts_required_team_name() -> None:
    result = TeamAwaitRequest.model_validate({"team_name": "alpha"})

    assert result.team_name == "alpha"


def test_team_await_request_rejects_empty_team_name() -> None:
    with pytest.raises(ValidationError):
        TeamAwaitRequest.model_validate({"team_name": ""})


def test_team_await_request_rejects_unexpected_extra_fields() -> None:
    with pytest.raises(ValidationError):
        TeamAwaitRequest.model_validate({"team_name": "alpha", "unexpected": True})


def test_team_status_snapshot_accepts_minimal_missing_team_payload() -> None:
    result = TeamStatusSnapshot.model_validate(
        {"team_name": "missing-team", "status": "missing"}
    )

    assert result.team_name == "missing-team"
    assert result.status == "missing"
    assert result.phase is None


def test_team_status_snapshot_accepts_optional_phase() -> None:
    result = TeamStatusSnapshot.model_validate(
        {"team_name": "alpha", "status": "active", "phase": "team-exec"}
    )

    assert result.team_name == "alpha"
    assert result.status == "active"
    assert result.phase == "team-exec"


def test_team_status_snapshot_rejects_unexpected_extra_fields() -> None:
    with pytest.raises(ValidationError):
        TeamStatusSnapshot.model_validate(
            {"team_name": "alpha", "status": "active", "unexpected": True}
        )


def test_team_await_snapshot_accepts_missing_team_result() -> None:
    result = TeamAwaitSnapshot.model_validate(
        {"team_name": "missing-team", "status": "missing"}
    )

    assert result.team_name == "missing-team"
    assert result.status == "missing"
    assert result.cursor is None
    assert result.event_type is None


def test_team_await_snapshot_accepts_cursor_and_event_type() -> None:
    result = TeamAwaitSnapshot.model_validate(
        {
            "team_name": "alpha",
            "status": "active",
            "cursor": "cursor-1",
            "event_type": "worker_completed",
        }
    )

    assert result.team_name == "alpha"
    assert result.status == "active"
    assert result.cursor == "cursor-1"
    assert result.event_type == "worker_completed"


def test_team_await_snapshot_rejects_unexpected_extra_fields() -> None:
    with pytest.raises(ValidationError):
        TeamAwaitSnapshot.model_validate(
            {
                "team_name": "alpha",
                "status": "active",
                "unexpected": True,
            }
        )
