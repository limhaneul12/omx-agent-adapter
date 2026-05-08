from importlib import import_module
from pathlib import Path


TEAMWORK_TYPE_MODULES = (
    "team_api_envelope",
    "team_api_raw_payloads",
    "team_api_data_specs",
    "team_api_transport_payloads",
    "team_command_transport_payloads",
)


def test_teamwork_adapter_types_are_split_by_team_concept() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    adapter_types_dir = repo_root / "src" / "omx_remote" / "adapter_types"
    teams_type_dir = adapter_types_dir / "teams_type"

    assert teams_type_dir.is_dir()
    assert not (adapter_types_dir / "teamwork_types.py").exists()

    for module_name in TEAMWORK_TYPE_MODULES:
        module = import_module(f"omx_remote.adapter_types.teams_type.{module_name}")
        assert module is not None


def test_team_api_envelope_uses_decoded_envelope_name() -> None:
    envelope_module = import_module(
        "omx_remote.adapter_types.teams_type.team_api_envelope"
    )

    assert hasattr(envelope_module, "TeamApiDecodedEnvelope")
    assert not hasattr(envelope_module, "TeamApiEnvelopeSpec")
