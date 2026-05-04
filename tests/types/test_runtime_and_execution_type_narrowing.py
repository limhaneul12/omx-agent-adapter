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
