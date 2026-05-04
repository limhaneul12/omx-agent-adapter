import asyncio
import inspect

import pytest
from pydantic import ValidationError

from omx_remote.schemas.teamwork_schemas import (
    TeamApiMailboxListRequest,
    TeamApiListTasksRequest,
    TeamApiReadConfigError,
    TeamApiReadConfigRequest,
    TeamApiReadEventsRequest,
    TeamApiReadManifestError,
    TeamApiReadManifestRequest,
    TeamApiReadMonitorSnapshotRequest,
)
from omx_remote.shared.exceptions.teamwork_exceptions import TeamworkSurfaceError
from omx_remote.teamwork import team_api_snapshot


class DummyResult:
    def __init__(self, stdout: str = "{}", stderr: str = "") -> None:
        self.stdout = stdout
        self.stderr = stderr


def test_read_team_api_list_tasks_is_async() -> None:
    assert inspect.iscoroutinefunction(team_api_snapshot.read_team_api_list_tasks)


def test_read_team_api_list_tasks_accepts_typed_request() -> None:
    coroutine = team_api_snapshot.read_team_api_list_tasks(
        TeamApiListTasksRequest(team_name="alpha")
    )

    assert inspect.isawaitable(coroutine)
    asyncio.run(coroutine)


def test_read_team_api_list_tasks_returns_empty_snapshot(monkeypatch) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","timestamp":"2026-05-02T14:20:07.659Z","command":"omx team api list-tasks","ok":true,"operation":"list-tasks","data":{"count":0,"tasks":[]}}\n'
        ),
    )

    result = asyncio.run(
        team_api_snapshot.read_team_api_list_tasks(
            TeamApiListTasksRequest(team_name="missing-team")
        )
    )

    assert result.count == 0
    assert result.tasks == []


def test_read_team_api_list_tasks_rejects_unparseable_json_transport(monkeypatch) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(stdout="not-json\n"),
    )

    with pytest.raises(TeamworkSurfaceError):
        asyncio.run(
            team_api_snapshot.read_team_api_list_tasks(
                TeamApiListTasksRequest(team_name="alpha")
            )
        )


def test_read_team_api_list_tasks_preserves_required_contract_validation(monkeypatch) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","ok":true,"data":{}}\n'
        ),
    )

    with pytest.raises(ValidationError):
        asyncio.run(
            team_api_snapshot.read_team_api_list_tasks(
                TeamApiListTasksRequest(team_name="alpha")
            )
        )


def test_read_team_api_list_tasks_normalizes_live_task_payload_shape(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","ok":true,"data":{"count":1,"tasks":[{"subject":"Team surface closure: status/await and team-api regressions","description":"Own src/teamwork/team_snapshot.py","status":"in_progress","owner":"worker-1","depends_on":[],"role":"executor","id":"1","version":3,"created_at":"2026-05-03T04:17:53.343Z","claim":{"owner":"worker-1","token":"claim-token","leased_until":"2026-05-03T04:33:35.285Z"},"requires_code_change":true}]}}\n'
        ),
    )

    result = asyncio.run(
        team_api_snapshot.read_team_api_list_tasks(
            TeamApiListTasksRequest(team_name="roadmap-closure-burnd-0cc0315d")
        )
    )

    assert result.count == 1
    assert result.tasks[0].id == "1"
    assert (
        result.tasks[0].subject
        == "Team surface closure: status/await and team-api regressions"
    )
    assert result.tasks[0].status == "in_progress"
    assert result.tasks[0].owner == "worker-1"


def test_read_team_api_list_tasks_rejects_count_mismatch(monkeypatch) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","ok":true,"data":{"count":2,"tasks":[{"id":"1","subject":"task","status":"pending","owner":"worker-1"}]}}\n'
        ),
    )

    with pytest.raises(TeamworkSurfaceError):
        asyncio.run(
            team_api_snapshot.read_team_api_list_tasks(
                TeamApiListTasksRequest(team_name="alpha")
            )
        )


def test_read_team_api_list_tasks_rejects_non_object_task_payload_item(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","ok":true,"data":{"count":1,"tasks":["not-a-task"]}}\n'
        ),
    )

    with pytest.raises(TeamworkSurfaceError):
        asyncio.run(
            team_api_snapshot.read_team_api_list_tasks(
                TeamApiListTasksRequest(team_name="alpha")
            )
        )


def test_read_team_api_read_events_is_async() -> None:
    assert inspect.iscoroutinefunction(team_api_snapshot.read_team_api_read_events)


def test_read_team_api_read_events_accepts_typed_request() -> None:
    coroutine = team_api_snapshot.read_team_api_read_events(
        TeamApiReadEventsRequest(team_name="alpha")
    )

    assert inspect.isawaitable(coroutine)
    asyncio.run(coroutine)


def test_read_team_api_read_events_returns_empty_snapshot(monkeypatch) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","timestamp":"2026-05-02T14:20:08.980Z","command":"omx team api read-events","ok":true,"operation":"read-events","data":{"count":0,"cursor":"","events":[]}}\n'
        ),
    )

    result = asyncio.run(
        team_api_snapshot.read_team_api_read_events(
            TeamApiReadEventsRequest(team_name="missing-team")
        )
    )

    assert result.count == 0
    assert result.cursor == ""
    assert result.events == []


def test_read_team_api_read_events_rejects_transport_error_payload(monkeypatch) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","ok":false,"error":{"code":"team_not_found","message":"team_not_found"}}\n'
        ),
    )

    with pytest.raises(TeamworkSurfaceError):
        asyncio.run(
            team_api_snapshot.read_team_api_read_events(
                TeamApiReadEventsRequest(team_name="missing-team")
            )
        )


def test_read_team_api_read_events_normalizes_live_event_payload_shape(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","ok":true,"data":{"count":2,"cursor":"cursor-1","events":[{"type":"message_received","worker":"leader-fixed","message_id":"message-1","event_id":"event-1","team":"roadmap-closure-burnd-0cc0315d","created_at":"2026-05-03T04:18:19.286Z"},{"type":"task_completed","worker":"worker-3","task_id":"4","message_id":null,"event_id":"event-2","team":"roadmap-closure-burnd-0cc0315d","created_at":"2026-05-03T04:21:34.354Z"}]}}\n'
        ),
    )

    result = asyncio.run(
        team_api_snapshot.read_team_api_read_events(
            TeamApiReadEventsRequest(team_name="roadmap-closure-burnd-0cc0315d")
        )
    )

    assert result.count == 2
    assert result.cursor == "cursor-1"
    assert result.events[0].type == "message_received"
    assert result.events[0].worker == "leader-fixed"
    assert result.events[0].message_id == "message-1"
    assert result.events[0].task_id is None
    assert result.events[1].type == "task_completed"
    assert result.events[1].worker == "worker-3"
    assert result.events[1].task_id == "4"


def test_read_team_api_read_events_rejects_count_mismatch(monkeypatch) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","ok":true,"data":{"count":2,"cursor":"cursor-1","events":[{"type":"message_received","worker":"leader-fixed","message_id":"message-1"}]}}\n'
        ),
    )

    with pytest.raises(TeamworkSurfaceError):
        asyncio.run(
            team_api_snapshot.read_team_api_read_events(
                TeamApiReadEventsRequest(team_name="alpha")
            )
        )


def test_load_team_api_payload_rejects_null_transport_payload() -> None:
    with pytest.raises(TeamworkSurfaceError):
        team_api_snapshot._load_team_api_payload(
            'null',
            "omx team api list-tasks",
        )


def test_load_team_api_payload_rejects_non_object_data_payload() -> None:
    with pytest.raises(TeamworkSurfaceError):
        team_api_snapshot._load_team_api_payload(
            '{"ok":true,"data":[]}',
            "omx team api list-tasks",
        )


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


def test_read_team_api_read_monitor_snapshot_is_async() -> None:
    assert inspect.iscoroutinefunction(team_api_snapshot.read_team_api_read_monitor_snapshot)


def test_read_team_api_read_monitor_snapshot_accepts_typed_request() -> None:
    coroutine = team_api_snapshot.read_team_api_read_monitor_snapshot(
        TeamApiReadMonitorSnapshotRequest(team_name="alpha")
    )

    assert inspect.isawaitable(coroutine)
    asyncio.run(coroutine)


def test_read_team_api_read_monitor_snapshot_returns_null_snapshot(monkeypatch) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","ok":true,"operation":"read-monitor-snapshot","data":{"snapshot":null}}\n'
        ),
    )

    result = asyncio.run(
        team_api_snapshot.read_team_api_read_monitor_snapshot(
            TeamApiReadMonitorSnapshotRequest(team_name="missing-team")
        )
    )

    assert result.snapshot is None


def test_read_team_api_read_monitor_snapshot_rejects_unparseable_json_transport(monkeypatch) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(stdout="not-json\n"),
    )

    with pytest.raises(TeamworkSurfaceError):
        asyncio.run(
            team_api_snapshot.read_team_api_read_monitor_snapshot(
                TeamApiReadMonitorSnapshotRequest(team_name="alpha")
            )
        )


def test_read_team_api_read_monitor_snapshot_preserves_missing_snapshot_as_none(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(stdout='{"schema_version":"1.0","ok":true,"data":{}}\n'),
    )

    result = asyncio.run(
        team_api_snapshot.read_team_api_read_monitor_snapshot(
            TeamApiReadMonitorSnapshotRequest(team_name="alpha")
        )
    )

    assert result.snapshot is None


def test_read_team_api_read_config_error_is_async() -> None:
    assert inspect.iscoroutinefunction(team_api_snapshot.read_team_api_read_config_error)


def test_read_team_api_read_config_error_accepts_typed_request() -> None:
    coroutine = team_api_snapshot.read_team_api_read_config_error(
        TeamApiReadConfigRequest(team_name="alpha")
    )

    assert inspect.isawaitable(coroutine)
    asyncio.run(coroutine)


def test_read_team_api_read_config_error_returns_typed_error_payload(monkeypatch) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","ok":false,"operation":"read-config","error":{"code":"team_not_found","message":"team_not_found"}}\n'
        ),
    )

    result = asyncio.run(
        team_api_snapshot.read_team_api_read_config_error(
            TeamApiReadConfigRequest(team_name="missing-team")
        )
    )

    assert isinstance(result, TeamApiReadConfigError)
    assert result.code == "team_not_found"
    assert result.message == "team_not_found"


def test_read_team_api_read_manifest_error_is_async() -> None:
    assert inspect.iscoroutinefunction(team_api_snapshot.read_team_api_read_manifest_error)


def test_read_team_api_read_manifest_error_accepts_typed_request() -> None:
    coroutine = team_api_snapshot.read_team_api_read_manifest_error(
        TeamApiReadManifestRequest(team_name="alpha")
    )

    assert inspect.isawaitable(coroutine)
    asyncio.run(coroutine)


def test_read_team_api_read_manifest_error_returns_typed_error_payload(monkeypatch) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","ok":false,"operation":"read-manifest","error":{"code":"manifest_not_found","message":"manifest_not_found"}}\n'
        ),
    )

    result = asyncio.run(
        team_api_snapshot.read_team_api_read_manifest_error(
            TeamApiReadManifestRequest(team_name="missing-team")
        )
    )

    assert isinstance(result, TeamApiReadManifestError)
    assert result.code == "manifest_not_found"
    assert result.message == "manifest_not_found"
