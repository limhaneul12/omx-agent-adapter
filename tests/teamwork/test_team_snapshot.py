import asyncio
import inspect

import pytest
from pydantic import ValidationError

from omx_remote.schemas.teamwork_schemas import TeamAwaitRequest, TeamStatusRequest
from omx_remote.shared.exceptions.teamwork_exceptions import TeamworkSurfaceError
from omx_remote.teamwork import team_snapshot


class DummyResult:
    def __init__(self, stdout: str = "{}", stderr: str = "") -> None:
        self.stdout = stdout
        self.stderr = stderr


def test_read_team_status_is_async() -> None:
    assert inspect.iscoroutinefunction(team_snapshot.read_team_status)


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

    assert result.dead_workers == []
    assert result.non_reporting_workers == ["worker-3"]


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
    assert result.dead_workers == ["worker-2"]
    assert result.non_reporting_workers == ["worker-3"]


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


def test_read_team_status_preserves_required_contract_validation(monkeypatch) -> None:
    monkeypatch.setattr(
        team_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(stdout='{"team_name":"alpha"}\n'),
    )

    with pytest.raises(ValidationError):
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


def test_await_team_status_ignores_non_object_event_payload(monkeypatch) -> None:
    monkeypatch.setattr(
        team_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"team_name":"alpha","status":"active","cursor":"cursor-1","event":[]}\n'
        ),
    )

    result = asyncio.run(
        team_snapshot.await_team_status(TeamAwaitRequest(team_name="alpha"))
    )

    assert result.cursor == "cursor-1"
    assert result.event_type is None
    assert result.event_worker is None
    assert result.event_task_id is None


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
