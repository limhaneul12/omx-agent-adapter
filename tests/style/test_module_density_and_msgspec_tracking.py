from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "src" / "omx_remote"


def test_execution_payload_mapping_compatibility_bucket_is_removed() -> None:
    execution_root = SOURCE_ROOT / "execution"

    assert not (execution_root / "payload_mapping.py").exists()
    assert (execution_root / "payload_transport.py").exists()
    assert (execution_root / "tool_interactions.py").exists()
    assert (execution_root / "contract_promotion.py").exists()


def test_goal_supervisor_prompt_rendering_is_split_by_subconcept() -> None:
    supervisor_path = SOURCE_ROOT / "runtime" / "goal" / "codex_goal_supervisor.py"
    prompt_path = SOURCE_ROOT / "runtime" / "goal" / "ralph_handoff_prompt.py"

    assert prompt_path.exists()
    assert len(supervisor_path.read_text().splitlines()) < 520


def test_json_extraction_hotspots_use_msgspec_contracts_instead_of_tracking_lists() -> None:
    assert not (
        SOURCE_ROOT / "adapter_types" / "type_contract" / "msgspec_tracking_contract_type.py"
    ).exists()

    assert "msgspec.convert" in (SOURCE_ROOT / "teamwork" / "team_api_transport.py").read_text()
    assert "msgspec.convert" in (SOURCE_ROOT / "teamwork" / "team_snapshot.py").read_text()
    assert "msgspec.convert" in (SOURCE_ROOT / "history" / "session_search.py").read_text()
