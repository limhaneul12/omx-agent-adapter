import asyncio
import inspect
from typing import get_args

import pytest

import omx_remote.adapter_types.teamwork_types as teamwork_types
from omx_remote.schemas.teamwork.status_schemas import (
    TeamAwaitRequest,
    TeamStatusRequest,
)
from omx_remote.shared.exceptions import TeamworkSurfaceError
from omx_remote.teamwork import team_snapshot


class DummyResult:
    def __init__(self, stdout: str = "{}", stderr: str = "") -> None:
        self.stdout = stdout
        self.stderr = stderr


def test_read_team_status_is_async() -> None:
    assert inspect.iscoroutinefunction(team_snapshot.read_team_status)


def test_team_status_and_await_specs_use_stable_transport_field_types() -> None:
    status_hints = teamwork_types.TeamStatusSpec.__annotations__
    await_hints = teamwork_types.TeamAwaitSpec.__annotations__
    event_hints = teamwork_types.TeamAwaitEventSpec.__annotations__

    assert status_hints["team_name"] is str
    assert status_hints["status"] is str
    assert get_args(status_hints["dead_workers"]) == (list[str], type(None))
    assert get_args(status_hints["non_reporting_workers"]) == (list[str], type(None))
    assert await_hints["team_name"] is str
    assert await_hints["status"] is str
    assert get_args(await_hints["event"]) == (
        teamwork_types.TeamAwaitEventSpec,
        type(None),
    )
    assert get_args(event_hints["type"]) == (str, type(None))
    assert get_args(event_hints["worker"]) == (str, type(None))
    assert get_args(event_hints["task_id"]) == (str, type(None))


def test_read_team_status_accepts_typed_request() -> None:
    coroutine = team_snapshot.read_team_status(TeamStatusRequest(team_name="alpha"))

    assert inspect.isawaitable(coroutine)
    asyncio.run(coroutine)


def test_read_team_status_returns_minimal_missing_team_snapshot(monkeypatch) -> None:
    monkeypatch.setattr(
        team_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"team_name":"missing-team","status":"missing"}\n'
        ),
    )

    result = asyncio.run(
        team_snapshot.read_team_status(TeamStatusRequest(team_name="missing-team"))
    )

    assert result.team_name == "missing-team"
    assert result.status == "missing"
    assert result.phase is None


def test_read_team_status_normalizes_current_phase_to_phase(monkeypatch) -> None:
    monkeypatch.setattr(
        team_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"team_name":"alpha","status":"active","current_phase":"team-exec"}\n'
        ),
    )

    result = asyncio.run(
        team_snapshot.read_team_status(TeamStatusRequest(team_name="alpha"))
    )

    assert result.team_name == "alpha"
    assert result.status == "active"
    assert result.phase == "team-exec"


def test_read_team_status_defaults_missing_worker_edge_lists_to_empty_lists(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        team_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"team_name":"alpha","status":"ok","phase":"team-exec","non_reporting_workers":["worker-3"]}\n'
        ),
    )

    result = asyncio.run(
        team_snapshot.read_team_status(TeamStatusRequest(team_name="alpha"))
    )

    assert result.dead_workers == ()
    assert result.non_reporting_workers == ("worker-3",)


def test_read_team_status_exposes_worker_edge_lists(monkeypatch) -> None:
    monkeypatch.setattr(
        team_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"team_name":"alpha","status":"ok","phase":"team-exec","dead_workers":["worker-2"],"non_reporting_workers":["worker-3"]}\n'
        ),
    )

    result = asyncio.run(
        team_snapshot.read_team_status(TeamStatusRequest(team_name="alpha"))
    )

    assert result.team_name == "alpha"
    assert result.status == "ok"
    assert result.phase == "team-exec"
    assert result.dead_workers == ("worker-2",)
    assert result.non_reporting_workers == ("worker-3",)


def test_read_team_status_rejects_unparseable_json_transport(monkeypatch) -> None:
    monkeypatch.setattr(
        team_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(stdout="not-json\n"),
    )

    with pytest.raises(TeamworkSurfaceError):
        asyncio.run(
            team_snapshot.read_team_status(TeamStatusRequest(team_name="alpha"))
        )


def test_read_team_status_rejects_missing_status_field(monkeypatch) -> None:
    monkeypatch.setattr(
        team_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(stdout='{"team_name":"alpha"}\n'),
    )

    with pytest.raises(TeamworkSurfaceError):
        asyncio.run(
            team_snapshot.read_team_status(TeamStatusRequest(team_name="alpha"))
        )


def test_await_team_status_returns_missing_team_snapshot(monkeypatch) -> None:
    monkeypatch.setattr(
        team_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"team_name":"missing-team","status":"missing"}\n'
        ),
    )

    result = asyncio.run(
        team_snapshot.await_team_status(TeamAwaitRequest(team_name="missing-team"))
    )

    assert result.team_name == "missing-team"
    assert result.status == "missing"
    assert result.cursor is None
    assert result.event_type is None


def test_await_team_status_normalizes_cursor_and_event_type(monkeypatch) -> None:
    monkeypatch.setattr(
        team_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"team_name":"alpha","status":"active","cursor":"cursor-1","event":{"type":"worker_completed","worker":"worker-1"}}\n'
        ),
    )

    result = asyncio.run(
        team_snapshot.await_team_status(TeamAwaitRequest(team_name="alpha"))
    )

    assert result.team_name == "alpha"
    assert result.status == "active"
    assert result.cursor == "cursor-1"
    assert result.event_type == "worker_completed"


def test_await_team_status_exposes_event_worker_and_task_id(monkeypatch) -> None:
    monkeypatch.setattr(
        team_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"team_name":"alpha","status":"event","cursor":"cursor-1","event":{"type":"task_completed","worker":"worker-3","task_id":"4"}}\n'
        ),
    )

    result = asyncio.run(
        team_snapshot.await_team_status(TeamAwaitRequest(team_name="alpha"))
    )

    assert result.status == "event"
    assert result.event_type == "task_completed"
    assert result.event_worker == "worker-3"
    assert result.event_task_id == "4"


def test_await_team_status_normalizes_empty_cursor_to_none(monkeypatch) -> None:
    monkeypatch.setattr(
        team_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"team_name":"missing-team","status":"missing","cursor":""}\n'
        ),
    )

    result = asyncio.run(
        team_snapshot.await_team_status(TeamAwaitRequest(team_name="missing-team"))
    )

    assert result.team_name == "missing-team"
    assert result.status == "missing"
    assert result.cursor is None
    assert result.event_type is None


def test_await_team_status_rejects_non_object_event_payload(monkeypatch) -> None:
    monkeypatch.setattr(
        team_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"team_name":"alpha","status":"active","cursor":"cursor-1","event":[]}\n'
        ),
    )

    with pytest.raises(TeamworkSurfaceError):
        asyncio.run(
            team_snapshot.await_team_status(TeamAwaitRequest(team_name="alpha"))
        )


def test_await_team_status_rejects_unparseable_json_transport(monkeypatch) -> None:
    monkeypatch.setattr(
        team_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(stdout="not-json\n"),
    )

    with pytest.raises(TeamworkSurfaceError):
        asyncio.run(
            team_snapshot.await_team_status(TeamAwaitRequest(team_name="alpha"))
        )


def test_load_team_status_transport_payload_rejects_non_object_transport() -> None:
    with pytest.raises(TeamworkSurfaceError):
        team_snapshot._load_team_status_transport_payload("[]")


def test_load_team_await_transport_payload_rejects_non_object_transport() -> None:
    with pytest.raises(TeamworkSurfaceError):
        team_snapshot._load_team_await_transport_payload("[]")
