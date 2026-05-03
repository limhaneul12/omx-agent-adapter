import pytest

from shared.exceptions.bridge_exceptions import BridgeSurfaceError
from shared.exceptions.runtime_exceptions import RuntimeSurfaceError
from shared.json_transport import load_json_object_stdout


def test_load_json_object_stdout_returns_mapping() -> None:
    result = load_json_object_stdout(
        '{"active_modes":["ralph"]}\n',
        command_name="omx state list-active",
        error_type=RuntimeSurfaceError,
    )

    assert result == {"active_modes": ["ralph"]}


def test_load_json_object_stdout_rejects_empty_stdout() -> None:
    with pytest.raises(
        BridgeSurfaceError,
        match="omx adapt probe returned no stdout output",
    ):
        load_json_object_stdout(
            "",
            command_name="omx adapt probe",
            error_type=BridgeSurfaceError,
        )


def test_load_json_object_stdout_rejects_unparseable_json() -> None:
    with pytest.raises(
        BridgeSurfaceError,
        match="omx adapt probe returned unparseable JSON output",
    ):
        load_json_object_stdout(
            "not-json\n",
            command_name="omx adapt probe",
            error_type=BridgeSurfaceError,
        )


def test_load_json_object_stdout_rejects_non_object_json() -> None:
    with pytest.raises(
        BridgeSurfaceError,
        match="omx adapt probe returned a non-object JSON payload",
    ):
        load_json_object_stdout(
            '["not","an","object"]\n',
            command_name="omx adapt probe",
            error_type=BridgeSurfaceError,
        )
