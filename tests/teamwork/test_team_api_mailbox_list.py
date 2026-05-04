import asyncio
import inspect

import pytest
from pydantic import ValidationError

from omx_remote.schemas.teamwork_schemas import TeamApiMailboxListRequest
from omx_remote.shared.exceptions.teamwork_exceptions import TeamworkSurfaceError
from omx_remote.teamwork import team_api_snapshot


class DummyResult:
    def __init__(self, stdout: str = "{}", stderr: str = "") -> None:
        self.stdout = stdout
        self.stderr = stderr


def test_read_team_api_mailbox_list_is_async() -> None:
    assert inspect.iscoroutinefunction(team_api_snapshot.read_team_api_mailbox_list)


def test_read_team_api_mailbox_list_accepts_typed_request() -> None:
    coroutine = team_api_snapshot.read_team_api_mailbox_list(
        TeamApiMailboxListRequest(team_name="alpha", worker="worker-1")
    )

    assert inspect.isawaitable(coroutine)
    asyncio.run(coroutine)


def test_read_team_api_mailbox_list_returns_empty_snapshot(monkeypatch) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","ok":true,"operation":"mailbox-list","data":{"worker":"worker-1","count":0,"messages":[]}}\n'
        ),
    )

    result = asyncio.run(
        team_api_snapshot.read_team_api_mailbox_list(
            TeamApiMailboxListRequest(team_name="alpha", worker="worker-1")
        )
    )

    assert result.worker == "worker-1"
    assert result.count == 0
    assert result.messages == []


def test_read_team_api_mailbox_list_rejects_unparseable_json_transport(monkeypatch) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(stdout="not-json\n"),
    )

    with pytest.raises(TeamworkSurfaceError):
        asyncio.run(
            team_api_snapshot.read_team_api_mailbox_list(
                TeamApiMailboxListRequest(team_name="alpha", worker="worker-1")
            )
        )


def test_read_team_api_mailbox_list_preserves_required_contract_validation(monkeypatch) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","ok":true,"data":{"count":1,"messages":[]}}\n'
        ),
    )

    with pytest.raises(ValidationError):
        asyncio.run(
            team_api_snapshot.read_team_api_mailbox_list(
                TeamApiMailboxListRequest(team_name="alpha", worker="worker-1")
            )
        )


def test_read_team_api_mailbox_list_normalizes_live_message_payload_shape(monkeypatch) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","ok":true,"data":{"worker":"worker-1","count":1,"messages":[{"id":"message-1","subject":"follow-up","body":"please re-run tests","delivered":false,"extra":"ignored"}]}}\n'
        ),
    )

    result = asyncio.run(
        team_api_snapshot.read_team_api_mailbox_list(
            TeamApiMailboxListRequest(team_name="alpha", worker="worker-1")
        )
    )

    assert result.worker == "worker-1"
    assert result.count == 1
    assert result.messages[0].id == "message-1"
    assert result.messages[0].subject == "follow-up"
    assert result.messages[0].body == "please re-run tests"
    assert result.messages[0].delivered is False


def test_read_team_api_mailbox_list_rejects_count_mismatch(monkeypatch) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","ok":true,"data":{"worker":"worker-1","count":2,"messages":[{"id":"message-1","subject":"follow-up","body":"please re-run tests","delivered":false}]}}\n'
        ),
    )

    with pytest.raises(TeamworkSurfaceError):
        asyncio.run(
            team_api_snapshot.read_team_api_mailbox_list(
                TeamApiMailboxListRequest(team_name="alpha", worker="worker-1")
            )
        )


def test_read_team_api_mailbox_list_rejects_non_object_message_payload_item(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","ok":true,"data":{"worker":"worker-1","count":1,"messages":["not-a-message"]}}\n'
        ),
    )

    with pytest.raises(TeamworkSurfaceError):
        asyncio.run(
            team_api_snapshot.read_team_api_mailbox_list(
                TeamApiMailboxListRequest(team_name="alpha", worker="worker-1")
            )
        )
