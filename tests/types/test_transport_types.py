from adapter_types.bridge_types import (
    AdapterEnvelopeNormalizedPayload,
    AdapterEnvelopeTransportPayload,
    AdapterProbeNormalizedPayload,
    AdapterProbeTransportPayload,
    AdapterStatusNormalizedPayload,
    AdapterStatusTransportPayload,
)
from adapter_types.execution_types import (
    ExecMessageNormalizedPayload,
    ExecOutputNormalizedPayload,
    ExecToolCallNormalizedPayload,
    ExecToolResultNormalizedPayload,
    ExecutionTransportPayload,
)
from adapter_types.history_types import (
    SessionSearchNormalizedPayload,
    SessionSearchTransportPayload,
)
from adapter_types.runtime_types import ActiveRuntimeModesTransportPayload
from adapter_types.teamwork_types import (
    TeamApiListTasksNormalizedPayload,
    TeamApiReadEventsNormalizedPayload,
    TeamApiTransportPayload,
    TeamAwaitNormalizedPayload,
    TeamAwaitTransportPayload,
    TeamStatusNormalizedPayload,
    TeamStatusTransportPayload,
)


def test_session_search_transport_and_normalized_payload_shapes() -> None:
    transport_payload: SessionSearchTransportPayload = {
        "query": "hermes",
        "searched_files": 3,
        "matched_sessions": 1,
        "results": [],
    }
    normalized_payload: SessionSearchNormalizedPayload = {
        "query": "hermes",
        "searched_files": 3,
        "matched_sessions": 1,
        "results": [],
    }

    assert transport_payload["query"] == normalized_payload["query"]


def test_team_api_transport_and_normalized_payload_shapes() -> None:
    transport_payload: TeamApiTransportPayload = {
        "count": 1,
        "cursor": "cursor-1",
        "events": [],
    }
    list_tasks_payload: TeamApiListTasksNormalizedPayload = {
        "count": 1,
        "tasks": [],
    }
    read_events_payload: TeamApiReadEventsNormalizedPayload = {
        "count": 1,
        "cursor": "cursor-1",
        "events": [],
    }

    assert transport_payload["count"] == list_tasks_payload["count"]
    assert read_events_payload["cursor"] == "cursor-1"


def test_team_status_and_await_payload_shapes() -> None:
    status_transport: TeamStatusTransportPayload = {
        "team_name": "alpha",
        "status": "active",
        "phase": "team-exec",
    }
    status_normalized: TeamStatusNormalizedPayload = {
        "team_name": "alpha",
        "status": "active",
        "phase": "team-exec",
        "dead_workers": [],
        "non_reporting_workers": [],
    }
    await_transport: TeamAwaitTransportPayload = {
        "team_name": "alpha",
        "status": "event",
        "cursor": "cursor-1",
    }
    await_normalized: TeamAwaitNormalizedPayload = {
        "team_name": "alpha",
        "status": "event",
        "cursor": "cursor-1",
        "event_type": None,
        "event_worker": None,
        "event_task_id": None,
    }

    assert status_transport["team_name"] == status_normalized["team_name"]
    assert await_transport["cursor"] == await_normalized["cursor"]


def test_active_runtime_modes_and_execution_payload_shapes() -> None:
    runtime_transport: ActiveRuntimeModesTransportPayload = {
        "active_modes": ["ralph"],
    }
    execution_transport: ExecutionTransportPayload = {
        "type": "tool_result",
        "tool_name": "grep",
        "call_id": "call-1",
        "text": "match",
    }
    message_normalized: ExecMessageNormalizedPayload = {
        "kind": "message",
        "text": "hello",
    }
    output_normalized: ExecOutputNormalizedPayload = {
        "kind": "output_text",
        "text": "hello",
    }
    tool_call_normalized: ExecToolCallNormalizedPayload = {
        "kind": "tool_call",
        "tool_name": "grep",
        "call_id": "call-1",
        "arguments": "{}",
    }
    tool_result_normalized: ExecToolResultNormalizedPayload = {
        "kind": "tool_result",
        "tool_name": "grep",
        "call_id": "call-1",
        "text": "match",
    }

    assert runtime_transport["active_modes"] == ["ralph"]
    assert execution_transport["tool_name"] == tool_call_normalized["tool_name"]
    assert message_normalized["kind"] == "message"
    assert output_normalized["kind"] == "output_text"
    assert tool_result_normalized["call_id"] == "call-1"


def test_adapter_transport_and_normalized_payload_shapes() -> None:
    probe_transport: AdapterProbeTransportPayload = {
        "target": "hermes",
        "phase": "ready",
        "summary": "ok",
        "capabilities": [],
    }
    probe_normalized: AdapterProbeNormalizedPayload = {
        "target": "hermes",
        "phase": "ready",
        "summary": "ok",
        "capabilities": [],
        "target_runtime_state": None,
        "target_runtime_detail": None,
    }
    status_transport: AdapterStatusTransportPayload = {
        "target": "hermes",
        "phase": "ready",
        "summary": "ok",
        "capabilities": [],
    }
    status_normalized: AdapterStatusNormalizedPayload = {
        "target": "hermes",
        "phase": "ready",
        "summary": "ok",
        "capabilities": [],
        "adapter_state": None,
        "adapter_detail": None,
        "target_runtime_state": None,
        "target_runtime_detail": None,
    }
    envelope_transport: AdapterEnvelopeTransportPayload = {
        "target": "hermes",
        "displayName": "Hermes",
        "summary": "ok",
        "capabilities": [],
    }
    envelope_normalized: AdapterEnvelopeNormalizedPayload = {
        "target": "hermes",
        "display_name": "Hermes",
        "summary": "ok",
        "capabilities": [],
        "target_runtime_state": None,
        "target_runtime_detail": None,
    }

    assert probe_transport["target"] == probe_normalized["target"]
    assert status_transport["phase"] == status_normalized["phase"]
    assert envelope_transport["displayName"] == envelope_normalized["display_name"]
