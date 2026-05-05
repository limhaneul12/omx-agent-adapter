from omx_remote.adapter_types.bridge_types import (
    AdapterEnvelopeNormalizedPayload,
    AdapterEnvelopeRuntimePayload,
    AdapterEnvelopeTransportPayload,
    AdapterProbeNormalizedPayload,
    AdapterProbeRuntimePayload,
    AdapterProbeTransportPayload,
    AdapterStatusNormalizedPayload,
    AdapterStatusRuntimePayload,
    AdapterStatusTransportPayload,
)
from omx_remote.adapter_types.execution_types import (
    ExecMessageNormalizedPayload,
    ExecOutputNormalizedPayload,
    ExecToolCallNormalizedPayload,
    ExecToolResultNormalizedPayload,
    ExecutionAgentMessageItemTransportPayload,
    ExecutionCommandExecutionItemTransportPayload,
    ExecutionItemCompletedTransportPayload,
    ExecutionItemTransportPayload,
    ExecutionThreadStartedTransportPayload,
    ExecutionTransportPayload,
    ExecutionTurnCompletedTransportPayload,
    ExecutionUsageTransportPayload,
)
from omx_remote.adapter_types.history_types import (
    SessionSearchNormalizedPayload,
    SessionSearchTransportPayload,
)
from omx_remote.adapter_types.runtime_types import (
    ActiveRuntimeModesTransportPayload,
    RuntimeModeStateNormalizedPayload,
    RuntimeModeStateTransportPayload,
)
from omx_remote.adapter_types.teamwork_types import (
    TeamApiEnvelopePayload,
    TeamApiErrorTransportPayload,
    TeamApiListTasksNormalizedPayload,
    TeamApiMailboxListNormalizedPayload,
    TeamApiReadEventsNormalizedPayload,
    TeamApiTransportPayload,
    TeamApiWorkerStatusNormalizedPayload,
    TeamAwaitNormalizedPayload,
    TeamAwaitTransportPayload,
    TeamStatusNormalizedPayload,
    TeamStatusTransportPayload,
)
from omx_remote.shared.omx_enums.execution_enums import ExecutionEventKind


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
    envelope_payload: TeamApiEnvelopePayload = {
        "ok": True,
        "data": {"count": 1, "cursor": "cursor-1", "events": []},
    }
    transport_payload: TeamApiTransportPayload = {
        "count": 1,
        "cursor": "cursor-1",
        "events": [],
    }
    error_payload: TeamApiErrorTransportPayload = {
        "code": "team_not_found",
        "message": "team_not_found",
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

    assert envelope_payload["ok"] is True
    assert transport_payload["count"] == list_tasks_payload["count"]
    assert read_events_payload["cursor"] == "cursor-1"
    assert mailbox_list_payload["worker"] == "worker-1"
    assert error_payload["code"] == "team_not_found"
    assert worker_status_payload["state"] == "unknown"


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
    runtime_state_transport: RuntimeModeStateTransportPayload = {
        "mode": "team",
        "exists": False,
    }
    runtime_state_normalized: RuntimeModeStateNormalizedPayload = {
        "mode": "team",
        "exists": False,
        "state": None,
    }
    thread_started_transport: ExecutionThreadStartedTransportPayload = {
        "type": ExecutionEventKind.THREAD_STARTED,
        "thread_id": "019df138-200f-7792-a307-5996bdf7b9d2",
    }
    agent_message_item_transport: ExecutionAgentMessageItemTransportPayload = {
        "id": "item_0",
        "type": "agent_message",
        "text": "OK",
    }
    item_transport: ExecutionItemTransportPayload = agent_message_item_transport
    command_item_transport: ExecutionCommandExecutionItemTransportPayload = {
        "id": "item_1",
        "type": "command_execution",
        "command": "/bin/zsh -lc pwd",
        "aggregated_output": "/Users/imhaneul/Documents/sky_document/project/omx-agent-adapter\n",
        "exit_code": 0,
        "status": "completed",
    }
    usage_transport: ExecutionUsageTransportPayload = {
        "input_tokens": 21848,
        "cached_input_tokens": 7552,
        "output_tokens": 5,
        "reasoning_output_tokens": 0,
    }
    turn_completed_transport: ExecutionTurnCompletedTransportPayload = {
        "type": ExecutionEventKind.TURN_COMPLETED,
        "usage": usage_transport,
    }
    item_completed_transport: ExecutionItemCompletedTransportPayload = {
        "type": ExecutionEventKind.ITEM_COMPLETED,
        "item": item_transport,
    }
    execution_transport: ExecutionTransportPayload = {
        "type": ExecutionEventKind.TURN_COMPLETED,
        "tool_name": "grep",
        "call_id": "call-1",
        "text": "match",
        "thread_id": "019df138-200f-7792-a307-5996bdf7b9d2",
        "usage": usage_transport,
        "item": item_transport,
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
    assert runtime_state_transport["mode"] == runtime_state_normalized["mode"]
    assert thread_started_transport["type"] == ExecutionEventKind.THREAD_STARTED
    assert thread_started_transport["thread_id"] == "019df138-200f-7792-a307-5996bdf7b9d2"
    assert turn_completed_transport["usage"]["cached_input_tokens"] == 7552
    assert item_completed_transport["item"]["type"] == "agent_message"
    assert execution_transport["tool_name"] == tool_call_normalized["tool_name"]
    assert execution_transport["thread_id"] == "019df138-200f-7792-a307-5996bdf7b9d2"
    assert execution_transport["usage"]["cached_input_tokens"] == 7552
    assert execution_transport["item"]["type"] == "agent_message"
    assert command_item_transport["type"] == "command_execution"
    assert command_item_transport["exit_code"] == 0
    assert command_item_transport["status"] == "completed"
    assert message_normalized["kind"] == "message"
    assert output_normalized["kind"] == "output_text"
    assert tool_result_normalized["call_id"] == "call-1"


def test_adapter_transport_and_normalized_payload_shapes() -> None:
    probe_runtime: AdapterProbeRuntimePayload = {
        "state": "unavailable",
        "detail": "missing",
        "evidence": {},
    }
    probe_transport: AdapterProbeTransportPayload = {
        "target": "hermes",
        "phase": "ready",
        "summary": "ok",
        "capabilities": [],
        "targetRuntime": probe_runtime,
    }
    probe_normalized: AdapterProbeNormalizedPayload = {
        "target": "hermes",
        "phase": "ready",
        "summary": "ok",
        "capabilities": [],
        "target_runtime_state": None,
        "target_runtime_detail": None,
    }
    status_runtime: AdapterStatusRuntimePayload = {
        "state": "not-initialized",
        "detail": "write init",
        "configPath": "/tmp/adapter.json",
        "envelopePath": "/tmp/envelope.json",
    }
    status_transport: AdapterStatusTransportPayload = {
        "target": "hermes",
        "phase": "ready",
        "summary": "ok",
        "capabilities": [],
        "adapter": status_runtime,
        "targetRuntime": probe_runtime,
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
    envelope_runtime: AdapterEnvelopeRuntimePayload = {
        "state": "unavailable",
        "detail": "missing",
        "evidence": {},
    }
    envelope_transport: AdapterEnvelopeTransportPayload = {
        "target": "hermes",
        "displayName": "Hermes",
        "summary": "ok",
        "capabilities": [],
        "targetRuntime": envelope_runtime,
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
    assert probe_transport["targetRuntime"]["evidence"] == {}
    assert status_transport["phase"] == status_normalized["phase"]
    assert status_transport["adapter"]["configPath"] == "/tmp/adapter.json"
    assert envelope_transport["displayName"] == envelope_normalized["display_name"]
    assert envelope_transport["targetRuntime"]["detail"] == "missing"
