def test_execution_aliases_live_in_adapter_types() -> None:
    from omx_remote.adapter_types.execution_types import (
        ExecutionContract,
        ExecutionPayload,
        RoutedExecutionPayload,
    )

    assert ExecutionPayload is not None
    assert ExecutionContract is not None
    assert RoutedExecutionPayload is not None


def test_execution_value_constants_live_in_adapter_type_modules() -> None:
    import omx_remote.adapter_types.execution_types as execution_types
    from omx_remote.adapter_types.type_contract.execution_contract_type import (
        ANOMALY_SUMMARIES,
        KNOWN_EXECUTION_EVENT_TYPES,
        PROMOTABLE_EXECUTION_PAYLOAD_TYPES,
    )

    assert not hasattr(execution_types, "PROMOTABLE_EXECUTION_PAYLOAD_TYPES")
    assert not hasattr(execution_types, "KNOWN_EXECUTION_EVENT_TYPES")
    assert not hasattr(execution_types, "ANOMALY_SUMMARIES")
    assert PROMOTABLE_EXECUTION_PAYLOAD_TYPES
    assert KNOWN_EXECUTION_EVENT_TYPES
    assert ANOMALY_SUMMARIES
