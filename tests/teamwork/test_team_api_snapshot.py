import asyncio
import inspect
from typing import get_args

import msgspec
import pytest

import omx_remote.adapter_types.teamwork_types as teamwork_types
from omx_remote.schemas.teamwork.api_request_schemas import (
    TeamApiListTasksRequest,
    TeamApiMailboxListRequest,
    TeamApiReadConfigRequest,
    TeamApiReadEventsRequest,
    TeamApiReadManifestRequest,
    TeamApiReadMonitorSnapshotRequest,
    TeamApiReadWorkerStatusRequest,
)
from omx_remote.schemas.teamwork.api_snapshot_schemas import (
    TeamApiReadConfigError,
    TeamApiReadConfigSnapshot,
    TeamApiReadManifestError,
    TeamApiWorkerStatusSnapshot,
)
from omx_remote.shared.exceptions import TeamworkSurfaceError
from omx_remote.teamwork import (
    team_api_normalizers,
    team_api_snapshot,
    team_api_transport,
)


class DummyResult:
    def __init__(self, stdout: str = "{}", stderr: str = "") -> None:
        self.stdout = stdout
        self.stderr = stderr


def test_read_team_api_list_tasks_is_async() -> None:
    assert inspect.iscoroutinefunction(team_api_snapshot.read_team_api_list_tasks)


def test_team_api_snapshot_uses_split_transport_and_normalizer_modules() -> None:
    assert hasattr(team_api_transport, "load_team_api_payload")
    assert hasattr(team_api_normalizers, "normalize_team_api_monitor_snapshot_result")


def test_team_api_transport_uses_operation_specific_msgspec_data_specs() -> None:
    assert issubclass(teamwork_types.TeamApiListTasksDataSpec, msgspec.Struct)
    assert issubclass(teamwork_types.TeamApiReadEventsDataSpec, msgspec.Struct)
    assert issubclass(teamwork_types.TeamApiMailboxListDataSpec, msgspec.Struct)
    assert issubclass(teamwork_types.TeamApiReadMonitorSnapshotDataSpec, msgspec.Struct)
    assert hasattr(team_api_transport, "load_team_api_list_tasks_payload")
    assert hasattr(team_api_transport, "load_team_api_read_events_payload")
    assert hasattr(team_api_transport, "load_team_api_mailbox_list_payload")
    assert hasattr(team_api_transport, "load_team_api_read_monitor_snapshot_payload")


def test_team_api_data_specs_reject_scalar_collection_items_at_transport_boundary() -> None:
    tasks_hint = teamwork_types.TeamApiListTasksDataSpec.__annotations__["tasks"]
    events_hint = teamwork_types.TeamApiReadEventsDataSpec.__annotations__["events"]
    messages_hint = teamwork_types.TeamApiMailboxListDataSpec.__annotations__["messages"]

    assert get_args(tasks_hint) == (teamwork_types.TeamApiRawTaskPayload,)
    assert get_args(events_hint) == (teamwork_types.TeamApiRawEventPayload,)
    assert get_args(messages_hint) == (teamwork_types.TeamApiRawMailboxMessagePayload,)


def test_team_api_transport_contracts_mark_stable_and_raw_boundaries() -> None:
    envelope_hints = teamwork_types.TeamApiEnvelopeSpec.__annotations__

    assert envelope_hints["ok"] is bool
    assert getattr(teamwork_types.TeamApiEnvelopePayload, "__extra_items__", None) is object
    assert getattr(teamwork_types.TeamApiTransportPayload, "__extra_items__", None) is object
    assert getattr(teamwork_types.TeamApiErrorTransportPayload, "__closed__", None) is True
    assert getattr(teamwork_types.TeamApiListTasksTransportPayload, "__closed__", None) is True
    assert getattr(teamwork_types.TeamApiReadEventsTransportPayload, "__closed__", None) is True
    assert getattr(teamwork_types.TeamApiMailboxListTransportPayload, "__closed__", None) is True
    assert (
        getattr(
            teamwork_types.TeamApiReadMonitorSnapshotTransportPayload,
            "__closed__",
            None,
        )
        is True
    )
    assert (
        getattr(teamwork_types.TeamApiReadWorkerStatusTransportPayload, "__closed__", None)
        is True
    )


def test_team_api_normalizer_preserves_missing_monitor_snapshot_as_none() -> None:
    result = team_api_normalizers.normalize_team_api_monitor_snapshot_result(
        team_api_transport.TeamApiTransportPayload()
    )

    assert result.snapshot is None


def test_team_api_normalizer_drops_non_object_config_payload() -> None:
    data_payload = team_api_transport.TeamApiTransportPayload(config=["not", "a", "config"])

    result = team_api_normalizers.normalize_team_api_config_snapshot_result(data_payload)

    assert result.config is None


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
    assert result.tasks == ()


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


def test_read_team_api_list_tasks_rejects_missing_tasks_at_transport_boundary(monkeypatch) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","ok":true,"data":{}}\n'
        ),
    )

    with pytest.raises(TeamworkSurfaceError):
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


def test_read_team_api_list_tasks_drops_unstable_task_transport_fields(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","ok":true,"data":{"count":1,"tasks":[{"subject":"Team surface closure: status/await and team-api regressions","description":"Own src/teamwork/team_snapshot.py","status":"in_progress","owner":"worker-1","depends_on":[],"role":"executor","id":"1","version":3,"created_at":"2026-05-03T04:17:53.343Z","claim":{"owner":"worker-1"},"requires_code_change":true}]}}\n'
        ),
    )

    result = asyncio.run(
        team_api_snapshot.read_team_api_list_tasks(
            TeamApiListTasksRequest(team_name="roadmap-closure-burnd-0cc0315d")
        )
    )

    assert result.model_dump(mode="json") == {
        "count": 1,
        "tasks": [
            {
                "id": "1",
                "subject": "Team surface closure: status/await and team-api regressions",
                "status": "in_progress",
                "owner": "worker-1",
            }
        ],
    }


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
    assert result.events == ()


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


def test_read_team_api_read_events_drops_unstable_event_transport_fields(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","ok":true,"data":{"count":1,"cursor":"cursor-1","events":[{"type":"message_received","worker":"leader-fixed","message_id":"message-1","event_id":"event-1","team":"roadmap-closure-burnd-0cc0315d","created_at":"2026-05-03T04:18:19.286Z"}]}}\n'
        ),
    )

    result = asyncio.run(
        team_api_snapshot.read_team_api_read_events(
            TeamApiReadEventsRequest(team_name="roadmap-closure-burnd-0cc0315d")
        )
    )

    assert result.model_dump(mode="json") == {
        "count": 1,
        "cursor": "cursor-1",
        "events": [
            {
                "type": "message_received",
                "worker": "leader-fixed",
                "task_id": None,
                "message_id": "message-1",
            }
        ],
    }


def test_load_team_api_payload_rejects_null_transport_payload() -> None:
    with pytest.raises(TeamworkSurfaceError):
        team_api_transport.load_team_api_payload(
            'null',
            "omx team api list-tasks",
        )


def test_load_team_api_payload_rejects_non_object_data_payload() -> None:
    with pytest.raises(TeamworkSurfaceError):
        team_api_transport.load_team_api_payload(
            '{"ok":true,"data":[]}',
            "omx team api list-tasks",
        )


def test_load_team_api_payload_rejects_non_boolean_ok_value() -> None:
    with pytest.raises(TeamworkSurfaceError):
        team_api_transport.load_team_api_payload(
            '{"ok":"true","data":{"count":0,"tasks":[]}}',
            "omx team api list-tasks",
        )


def test_load_team_api_list_tasks_payload_rejects_missing_count() -> None:
    with pytest.raises(TeamworkSurfaceError):
        team_api_transport.load_team_api_list_tasks_payload(
            '{"ok":true,"data":{"tasks":[]}}'
        )


def test_load_team_api_list_tasks_payload_rejects_non_list_tasks() -> None:
    with pytest.raises(TeamworkSurfaceError):
        team_api_transport.load_team_api_list_tasks_payload(
            '{"ok":true,"data":{"count":1,"tasks":{"id":"not-a-list"}}}'
        )


def test_load_team_api_list_tasks_payload_rejects_non_object_task_items() -> None:
    with pytest.raises(TeamworkSurfaceError):
        team_api_transport.load_team_api_list_tasks_payload(
            '{"ok":true,"data":{"count":1,"tasks":["not-a-task"]}}'
        )


def test_load_team_api_read_events_payload_rejects_missing_cursor() -> None:
    with pytest.raises(TeamworkSurfaceError):
        team_api_transport.load_team_api_read_events_payload(
            '{"ok":true,"data":{"count":0,"events":[]}}'
        )


def test_load_team_api_read_events_payload_rejects_non_list_events() -> None:
    with pytest.raises(TeamworkSurfaceError):
        team_api_transport.load_team_api_read_events_payload(
            '{"ok":true,"data":{"count":1,"cursor":"cursor-1","events":"not-a-list"}}'
        )


def test_load_team_api_read_events_payload_rejects_non_object_event_items() -> None:
    with pytest.raises(TeamworkSurfaceError):
        team_api_transport.load_team_api_read_events_payload(
            '{"ok":true,"data":{"count":1,"cursor":"cursor-1","events":[123]}}'
        )


def test_load_team_api_mailbox_list_payload_rejects_missing_count() -> None:
    with pytest.raises(TeamworkSurfaceError):
        team_api_transport.load_team_api_mailbox_list_payload(
            '{"ok":true,"data":{"worker":"worker-1","messages":[]}}'
        )


def test_load_team_api_mailbox_list_payload_rejects_non_list_messages() -> None:
    with pytest.raises(TeamworkSurfaceError):
        team_api_transport.load_team_api_mailbox_list_payload(
            '{"ok":true,"data":{"worker":"worker-1","count":1,"messages":123}}'
        )


def test_load_team_api_mailbox_list_payload_rejects_non_object_message_items() -> None:
    with pytest.raises(TeamworkSurfaceError):
        team_api_transport.load_team_api_mailbox_list_payload(
            '{"ok":true,"data":{"worker":"worker-1","count":1,"messages":[false]}}'
        )


def test_read_team_api_list_tasks_rejects_non_list_tasks_as_surface_error(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","ok":true,"data":{"count":1,"tasks":{"id":"not-a-list"}}}\n'
        ),
    )

    with pytest.raises(TeamworkSurfaceError):
        asyncio.run(
            team_api_snapshot.read_team_api_list_tasks(
                TeamApiListTasksRequest(team_name="alpha")
            )
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
    assert result.messages == ()


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


def test_read_team_api_mailbox_list_rejects_missing_worker_at_transport_boundary(monkeypatch) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","ok":true,"data":{"count":1,"messages":[]}}\n'
        ),
    )

    with pytest.raises(TeamworkSurfaceError):
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


def test_read_team_api_read_config_returns_typed_snapshot(monkeypatch) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","ok":true,"operation":"read-config","data":{"config":{"name":"alpha","worker_count":2,"workers":[{"name":"worker-1"}]}}}\n'
        ),
    )

    result = asyncio.run(
        team_api_snapshot.read_team_api_read_config(
            TeamApiReadConfigRequest(team_name="alpha")
        )
    )

    assert isinstance(result, TeamApiReadConfigSnapshot)
    assert result.config == {
        "name": "alpha",
        "worker_count": 2,
        "workers": [{"name": "worker-1"}],
    }


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


def test_read_team_api_read_worker_status_is_async() -> None:
    assert inspect.iscoroutinefunction(team_api_snapshot.read_team_api_read_worker_status)


def test_read_team_api_read_worker_status_accepts_typed_request() -> None:
    coroutine = team_api_snapshot.read_team_api_read_worker_status(
        TeamApiReadWorkerStatusRequest(team_name="alpha", worker="worker-1")
    )

    assert inspect.isawaitable(coroutine)
    asyncio.run(coroutine)


def test_read_team_api_read_worker_status_returns_typed_snapshot(monkeypatch) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","ok":true,"operation":"read-worker-status","data":{"worker":"worker-1","status":{"state":"unknown","updated_at":"1970-01-01T00:00:00.000Z"}}}\n'
        ),
    )

    result = asyncio.run(
        team_api_snapshot.read_team_api_read_worker_status(
            TeamApiReadWorkerStatusRequest(team_name="alpha", worker="worker-1")
        )
    )

    assert isinstance(result, TeamApiWorkerStatusSnapshot)
    assert result.worker == "worker-1"
    assert result.state == "unknown"
    assert result.updated_at == "1970-01-01T00:00:00.000Z"


def test_read_team_api_read_worker_status_rejects_non_object_status_payload(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        team_api_snapshot,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"schema_version":"1.0","ok":true,"data":{"worker":"worker-1","status":[]}}\n'
        ),
    )

    with pytest.raises(TeamworkSurfaceError):
        asyncio.run(
            team_api_snapshot.read_team_api_read_worker_status(
                TeamApiReadWorkerStatusRequest(team_name="alpha", worker="worker-1")
            )
        )
