from pathlib import Path


def test_execution_value_contracts_live_under_type_contract_package() -> None:
    import omx_remote.adapter_types.execution_types as execution_types
    import omx_remote.execution.payload_transport as payload_transport
    from omx_remote.adapter_types.type_contract.execution_contract_type import (
        ANOMALY_SUMMARIES,
        KNOWN_EXECUTION_EVENT_TYPES,
        PROMOTABLE_EXECUTION_PAYLOAD_TYPES,
    )
    from omx_remote.adapter_types.type_contract.execution_payload_normalizer_contract_type import (
        EXECUTION_EVENT_PAYLOAD_NORMALIZERS,
    )
    from omx_remote.adapter_types.type_contract.execution_transport_contract_type import (
        EXECUTION_ITEM_STABLE_FIELD_KEYS,
        EXECUTION_TRANSPORT_STABLE_FIELD_KEYS,
    )
    from omx_remote.shared.omx_enums.execution_enums import (
        ExecutionEventKind,
        ExecutionItemStableFieldKey,
        ExecutionTransportStableFieldKey,
    )

    assert not hasattr(execution_types, "PROMOTABLE_EXECUTION_PAYLOAD_TYPES")
    assert not hasattr(execution_types, "KNOWN_EXECUTION_EVENT_TYPES")
    assert not hasattr(execution_types, "ANOMALY_SUMMARIES")
    assert PROMOTABLE_EXECUTION_PAYLOAD_TYPES
    assert KNOWN_EXECUTION_EVENT_TYPES
    assert ANOMALY_SUMMARIES
    assert not Path("src/omx_remote/adapter_types/execution_payload_contracts.py").exists()
    assert ExecutionItemStableFieldKey.ID.value in EXECUTION_ITEM_STABLE_FIELD_KEYS
    assert ExecutionTransportStableFieldKey.THREAD_ID.value in EXECUTION_TRANSPORT_STABLE_FIELD_KEYS
    assert ExecutionEventKind.ITEM_COMPLETED in EXECUTION_EVENT_PAYLOAD_NORMALIZERS
    assert not hasattr(payload_transport, "EXECUTION_ITEM_STABLE_FIELD_KEYS")
    assert not hasattr(payload_transport, "EXECUTION_TRANSPORT_STABLE_FIELD_KEYS")
    assert not hasattr(payload_transport, "EXECUTION_EVENT_PAYLOAD_NORMALIZERS")


def test_runtime_status_value_contracts_live_under_type_contract_package() -> None:
    import omx_remote.runtime.status.runtime_snapshot as runtime_snapshot
    from omx_remote.adapter_types.type_contract.runtime_status_contract_type import (
        ACTIVE_MODE_MARKER,
        IDLE_RUNTIME_SUMMARY,
        KNOWN_MODE_STATUS_MARKERS,
        RUNTIME_STATUS_PREFIXES,
    )
    from omx_remote.schemas.runtime.status_schemas import RuntimeModeStatus

    assert IDLE_RUNTIME_SUMMARY == "No active modes."
    assert ACTIVE_MODE_MARKER == RuntimeModeStatus.ACTIVE
    assert RuntimeModeStatus.UNKNOWN in KNOWN_MODE_STATUS_MARKERS
    assert ("inactive", RuntimeModeStatus.IDLE) in RUNTIME_STATUS_PREFIXES
    assert not hasattr(runtime_snapshot, "IDLE_RUNTIME_SUMMARY")
    assert not hasattr(runtime_snapshot, "ACTIVE_MODE_MARKER")
    assert not hasattr(runtime_snapshot, "KNOWN_MODE_STATUS_MARKERS")
    assert not hasattr(runtime_snapshot, "RUNTIME_STATUS_PREFIXES")


def test_ultrawork_classifier_contracts_live_under_type_contract_package() -> None:
    import omx_remote.adapter_types.ultrawork_types as ultrawork_types
    from omx_remote.adapter_types.type_contract.ultrawork_contract_type import (
        ULTRAWORK_NON_TERMINAL_OUTCOMES,
        ULTRAWORK_NON_TERMINAL_PHASES,
        ULTRAWORK_TERMINAL_OUTCOMES,
        ULTRAWORK_TERMINAL_PHASES,
    )
    from omx_remote.runtime.ultrawork.ultrawork_control import UltraworkStateClassifier

    assert not hasattr(ultrawork_types, "ULTRAWORK_TERMINAL_PHASES")
    assert not hasattr(ultrawork_types, "ULTRAWORK_NON_TERMINAL_PHASES")
    assert not hasattr(ultrawork_types, "ULTRAWORK_TERMINAL_OUTCOMES")
    assert not hasattr(ultrawork_types, "ULTRAWORK_NON_TERMINAL_OUTCOMES")
    assert ULTRAWORK_TERMINAL_PHASES
    assert ULTRAWORK_NON_TERMINAL_PHASES
    assert ULTRAWORK_TERMINAL_OUTCOMES
    assert ULTRAWORK_NON_TERMINAL_OUTCOMES
    assert "TERMINAL_PHASES" not in UltraworkStateClassifier.__dict__
    assert "NON_TERMINAL_PHASES" not in UltraworkStateClassifier.__dict__
    assert "TERMINAL_OUTCOMES" not in UltraworkStateClassifier.__dict__
    assert "NON_TERMINAL_OUTCOMES" not in UltraworkStateClassifier.__dict__


def test_operator_value_contracts_live_under_type_contract_package() -> None:
    import omx_remote.runtime.operators.multi_operator as multi_operator
    from omx_remote.adapter_types.type_contract.operator_contract_type import (
        ACTIONABLE_NEXT_ACTIONS,
        ACTIVE_LOOP_STATES,
        BLOCKING_LOOP_STATES,
    )
    from omx_remote.shared.omx_enums.multi_operator_enums import ManagedInterventionAction
    from omx_remote.shared.omx_enums.operator_enums import OperatorLoopState

    assert ManagedInterventionAction.LAUNCH in ACTIONABLE_NEXT_ACTIONS
    assert OperatorLoopState.SUCCESS in ACTIVE_LOOP_STATES
    assert OperatorLoopState.TERMINAL_FAILURE in BLOCKING_LOOP_STATES
    assert not hasattr(multi_operator, "_ACTIONABLE_NEXT_ACTIONS")
    assert not hasattr(multi_operator, "_ACTIVE_LOOP_STATES")
