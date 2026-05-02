import pytest
from pydantic import ValidationError

from schemas.teamwork_schemas import TeamAwaitRequest, TeamStatusRequest


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
