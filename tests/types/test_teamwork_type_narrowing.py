from omx_remote.adapter_types.teams_type.team_api_transport_payloads import (
    TeamApiEnvelopePayload,
    TeamApiErrorTransportPayload,
    TeamApiListTasksNormalizedPayload,
    TeamApiMailboxListNormalizedPayload,
    TeamApiReadEventsNormalizedPayload,
    TeamApiTransportEventPayload,
    TeamApiTransportMailboxMessagePayload,
    TeamApiTransportPayload,
    TeamApiTransportTaskPayload,
    TeamApiTransportWorkerStatusPayload,
    TeamApiWorkerStatusNormalizedPayload,
)
from omx_remote.adapter_types.teams_type.team_command_transport_payloads import (
    TeamAwaitNormalizedPayload,
    TeamAwaitTransportEventPayload,
    TeamAwaitTransportPayload,
    TeamStatusNormalizedPayload,
    TeamStatusTransportPayload,
)


def test_teamwork_typed_dicts_accept_narrowed_stable_shapes() -> None:
    envelope_payload: TeamApiEnvelopePayload = {
        "ok": True,
        "data": {"count": 0, "tasks": []},
    }
    error_payload: TeamApiErrorTransportPayload = {
        "code": "team_not_found",
        "message": "team_not_found",
    }
    transport_payload: TeamApiTransportPayload = {
        "count": 0,
        "cursor": "",
        "worker": "worker-1",
        "events": [],
        "tasks": [],
        "messages": [],
    }
    list_tasks_payload: TeamApiListTasksNormalizedPayload = {
        "count": 0,
        "tasks": [],
    }
    read_events_payload: TeamApiReadEventsNormalizedPayload = {
        "count": 0,
        "cursor": "",
        "events": [],
    }
    mailbox_list_payload: TeamApiMailboxListNormalizedPayload = {
        "worker": "worker-1",
        "count": 0,
        "messages": [],
    }
    worker_status_payload: TeamApiWorkerStatusNormalizedPayload = {
        "worker": "worker-1",
        "state": "unknown",
        "updated_at": "1970-01-01T00:00:00.000Z",
    }
    task_payload: TeamApiTransportTaskPayload = {
        "id": "1",
        "subject": "task",
        "status": "pending",
        "owner": "worker-1",
    }
    event_payload: TeamApiTransportEventPayload = {
        "type": "message_received",
        "worker": "worker-1",
        "task_id": "1",
        "message_id": "message-1",
    }
    mailbox_message_payload: TeamApiTransportMailboxMessagePayload = {
        "id": "message-1",
        "subject": "subject",
        "body": "body",
        "delivered": True,
    }
    transport_worker_status_payload: TeamApiTransportWorkerStatusPayload = {
        "state": "unknown",
        "updated_at": "1970-01-01T00:00:00.000Z",
    }
    team_status_transport: TeamStatusTransportPayload = {
        "team_name": "missing-team",
        "status": "missing",
        "current_phase": "cancelled",
        "dead_workers": [],
        "non_reporting_workers": [],
    }
    team_status_normalized: TeamStatusNormalizedPayload = {
        "team_name": "missing-team",
        "status": "missing",
        "phase": "cancelled",
        "dead_workers": [],
        "non_reporting_workers": [],
    }
    await_event_payload: TeamAwaitTransportEventPayload = {
        "type": "message_received",
        "worker": "worker-1",
        "task_id": "1",
    }
    await_transport: TeamAwaitTransportPayload = {
        "team_name": "missing-team",
        "status": "missing",
        "cursor": "",
        "event": None,
    }
    await_normalized: TeamAwaitNormalizedPayload = {
        "team_name": "missing-team",
        "status": "missing",
        "cursor": None,
        "event_type": None,
        "event_worker": None,
        "event_task_id": None,
    }

    assert envelope_payload["ok"] is True
    assert error_payload["code"] == "team_not_found"
    assert transport_payload["worker"] == "worker-1"
    assert list_tasks_payload["count"] == 0
    assert read_events_payload["cursor"] == ""
    assert mailbox_list_payload["worker"] == "worker-1"
    assert worker_status_payload["updated_at"] == "1970-01-01T00:00:00.000Z"
    assert task_payload["id"] == "1"
    assert event_payload["message_id"] == "message-1"
    assert mailbox_message_payload["delivered"] is True
    assert transport_worker_status_payload["state"] == "unknown"
    assert team_status_transport["team_name"] == "missing-team"
    assert team_status_normalized["phase"] == "cancelled"
    assert await_event_payload["task_id"] == "1"
    assert await_transport["status"] == "missing"
    assert await_normalized["cursor"] is None
