import inspect
from collections.abc import Callable

import msgspec

from omx_remote.execution import codex_invoke, invoke
from omx_remote.execution import payload_transport


def _assert_google_docstring(function: Callable[..., object]) -> None:
    docstring = inspect.getdoc(function)
    signature = inspect.signature(function)

    assert docstring is not None
    assert docstring.splitlines()[0].endswith(".")
    if signature.parameters:
        assert "Args:" in docstring
        for parameter_name in signature.parameters:
            assert f"{parameter_name} [" in docstring
    if signature.return_annotation is not inspect.Signature.empty:
        assert "Returns:" in docstring
        assert ":" in docstring.split("Returns:", 1)[1]


def test_payload_mapping_helpers_keep_google_docstring_sections() -> None:
    functions = [
        payload_transport._normalize_execution_event_type,
        payload_transport._normalize_execution_item_payload,
        payload_transport._normalize_execution_usage_payload,
        payload_transport._normalize_execution_thread_started_payload,
        payload_transport._normalize_execution_turn_completed_payload,
        payload_transport._normalize_execution_item_completed_payload,
        payload_transport._normalize_execution_event_payload,
        payload_transport._load_execution_transport_payload,
        payload_transport.load_execution_payload,
    ]

    for function in functions:
        _assert_google_docstring(function)


def test_invoke_helpers_keep_google_docstring_sections() -> None:
    functions = [
        invoke._command_failure_exit_code,
        invoke._normalize_completed_process_stream_text,
        invoke.run_omx_command,
    ]

    for function in functions:
        _assert_google_docstring(function)


def test_codex_invoke_helpers_keep_google_docstring_sections() -> None:
    functions = [
        codex_invoke._normalize_stream_text,
        codex_invoke._read_process_id_from_tmux_session,
        codex_invoke.spawn_codex_goal_session,
        codex_invoke.is_codex_goal_session_active,
    ]

    for function in functions:
        _assert_google_docstring(function)


def test_execution_transport_specs_are_msgspec_structs() -> None:
    from omx_remote.adapter_types.execution_types import (
        ExecutionItemSpec,
        ExecutionTransportSpec,
        ExecutionUsageSpec,
    )

    assert issubclass(ExecutionItemSpec, msgspec.Struct)
    assert issubclass(ExecutionTransportSpec, msgspec.Struct)
    assert issubclass(ExecutionUsageSpec, msgspec.Struct)


def test_execution_contract_constants_live_under_adapter_types() -> None:
    from pathlib import Path

    from omx_remote.adapter_types.type_contract.execution_contract_type import (
        ANOMALY_SUMMARIES,
        KNOWN_EXECUTION_EVENT_TYPES,
        PROMOTABLE_EXECUTION_PAYLOAD_TYPES,
    )

    assert PROMOTABLE_EXECUTION_PAYLOAD_TYPES
    assert KNOWN_EXECUTION_EVENT_TYPES
    assert ANOMALY_SUMMARIES
    assert not Path("src/omx_remote/adapter_types/execution_payload_contracts.py").exists()


def test_execution_contract_promotion_uses_explicit_dispatch_registry() -> None:
    from omx_remote.execution.contract_promotion import EXECUTION_CONTRACT_PROMOTERS
    from omx_remote.shared.omx_enums.execution_enums import PromotableExecutionPayloadType

    assert set(EXECUTION_CONTRACT_PROMOTERS) == set(PromotableExecutionPayloadType)
