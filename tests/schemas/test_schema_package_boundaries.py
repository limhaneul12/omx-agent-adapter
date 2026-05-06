from pathlib import Path


def test_schema_concepts_do_not_keep_flat_root_modules() -> None:
    schemas_root = Path("src/omx_remote/schemas")

    assert not (schemas_root / "execution_schemas.py").exists()
    assert not (schemas_root / "history_schemas.py").exists()
    assert not (schemas_root / "bridge_schemas.py").exists()
    assert not (schemas_root / "invoke_schemas.py").exists()

    assert (schemas_root / "execution" / "request_schemas.py").exists()
    assert (schemas_root / "execution" / "event_schemas.py").exists()
    assert (schemas_root / "execution" / "interaction_schemas.py").exists()
    assert (schemas_root / "history" / "session_schemas.py").exists()
    assert (schemas_root / "bridge" / "adapter_schemas.py").exists()
    assert (schemas_root / "invoke" / "command_schemas.py").exists()


def test_schema_concept_modules_expose_existing_contracts_directly() -> None:
    from omx_remote.schemas.bridge.adapter_schemas import AdapterProbeRequest
    from omx_remote.schemas.execution.event_schemas import ExecToolCall
    from omx_remote.schemas.execution.interaction_schemas import ToolInteractionReport
    from omx_remote.schemas.execution.request_schemas import ExecRequest
    from omx_remote.schemas.history.session_schemas import SessionSearchRequest
    from omx_remote.schemas.invoke.command_schemas import OmxCommandResult

    assert AdapterProbeRequest is not None
    assert ExecRequest is not None
    assert ExecToolCall is not None
    assert ToolInteractionReport is not None
    assert SessionSearchRequest is not None
    assert OmxCommandResult is not None
