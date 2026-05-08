from omx_remote.adapter_types.execution_types import (
    ExecutionAgentMessageItemTransportPayload,
    ExecutionCommandExecutionItemTransportPayload,
    ExecutionItemTransportPayload,
    ExecutionThreadStartedTransportPayload,
    ExecutionTransportPayload,
    ExecutionTurnCompletedTransportPayload,
    ExecutionUsageTransportPayload,
)
from omx_remote.adapter_types.runtime_types import (
    ActiveRuntimeModesTransportPayload,
    RuntimeModeStateNormalizedPayload,
    RuntimeModeStateTransportPayload,
    RuntimeModeStatusDataPayload,
    RuntimeModeStatusEntryPayload,
    RuntimeModeStatusResultNormalizedPayload,
    RuntimeModeStatusTransportPayload,
)
from omx_remote.shared.omx_enums.execution_enums import (
    ExecutionAnomalyCategory,
    ExecutionEventKind,
    ExecutionPayloadKind,
    ToolInteractionState,
)


def test_execution_enum_types_expose_stable_string_values() -> None:
    assert ToolInteractionState.COMPLETED == "completed"
    assert ToolInteractionState.MISSING_RESULT == "missing_result"
    assert ExecutionAnomalyCategory.UNMATCHED_RESULT == "unmatched_result"
    assert ExecutionAnomalyCategory.DUPLICATE_RESULT == "duplicate_result"
    assert ExecutionAnomalyCategory.MISSING_RESULT == "missing_result"
    assert ExecutionEventKind.THREAD_STARTED == "thread.started"
    assert ExecutionPayloadKind.COMMAND_EXECUTION == "command_execution"


def test_runtime_transport_payload_types_accept_narrowed_stable_shapes() -> None:
    active_modes_transport: ActiveRuntimeModesTransportPayload = {
        "active_modes": ["ralph", "team"],
    }
    mode_state_transport: RuntimeModeStateTransportPayload = {
        "mode": "ralph",
        "exists": True,
        "state": {"status": "active"},
    }
    mode_state_normalized: RuntimeModeStateNormalizedPayload = {
        "mode": "ralph",
        "exists": True,
        "state": {"status": "active"},
    }
    mode_status_transport: RuntimeModeStatusTransportPayload = {
        "statuses": {
            "ralph": {
                "active": True,
                "phase": "starting",
                "path": ".omx/state/ralph-state.json",
                "data": {"current_phase": "starting"},
            }
        }
    }
    mode_status_entry: RuntimeModeStatusEntryPayload = {
        "active": True,
        "phase": "starting",
        "path": ".omx/state/ralph-state.json",
        "data": {"current_phase": "starting"},
    }
    mode_status_data: RuntimeModeStatusDataPayload = {
        "current_phase": "starting",
    }
    mode_status_result: RuntimeModeStatusResultNormalizedPayload = {
        "requested_mode": "ralph",
        "found": True,
        "mode_snapshot": {
            "name": "ralph",
            "is_active": True,
            "phase": "starting",
            "state_path": ".omx/state/ralph-state.json",
        },
    }

    assert active_modes_transport["active_modes"] == ["ralph", "team"]
    assert mode_state_transport["exists"] is True
    assert mode_state_normalized["mode"] == "ralph"
    assert mode_status_transport["statuses"]["ralph"]["active"] is True
    assert mode_status_entry["path"] == ".omx/state/ralph-state.json"
    assert mode_status_data["current_phase"] == "starting"
    assert mode_status_result["requested_mode"] == "ralph"


def test_execution_transport_payload_types_accept_enum_narrowing() -> None:
    thread_started_transport: ExecutionThreadStartedTransportPayload = {
        "type": ExecutionEventKind.THREAD_STARTED,
        "thread_id": "019df138-200f-7792-a307-5996bdf7b9d2",
    }
    turn_completed_transport: ExecutionTurnCompletedTransportPayload = {
        "type": ExecutionEventKind.TURN_COMPLETED,
        "usage": {
            "input_tokens": 21848,
            "cached_input_tokens": 7552,
            "output_tokens": 5,
            "reasoning_output_tokens": 0,
        },
    }

    assert thread_started_transport["type"] == ExecutionEventKind.THREAD_STARTED
    assert turn_completed_transport["type"] == ExecutionEventKind.TURN_COMPLETED


def test_execution_transport_payload_types_keep_raw_passthrough_extras() -> None:
    unknown_item_transport: ExecutionItemTransportPayload = {
        "type": "custom_item",
        "payload": {"nested": True},
    }
    unknown_event_transport: ExecutionTransportPayload = {
        "type": "session.configured",
        "payload": {"mode": "agent"},
    }

    assert getattr(ExecutionUsageTransportPayload, "__closed__", False) is True
    assert getattr(ExecutionAgentMessageItemTransportPayload, "__closed__", False) is True
    assert getattr(ExecutionCommandExecutionItemTransportPayload, "__closed__", False) is True
    assert getattr(ExecutionItemTransportPayload, "__extra_items__", None) is object
    assert getattr(ExecutionTransportPayload, "__extra_items__", None) is object
    assert unknown_item_transport["payload"] == {"nested": True}
    assert unknown_event_transport["payload"] == {"mode": "agent"}
