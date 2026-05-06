import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "src" / "omx_remote"


def _function_if_count(source_path: Path, function_name: str) -> int:
    module_tree = ast.parse(source_path.read_text(), filename=str(source_path))
    for node in ast.walk(module_tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == function_name:
            if_count: int = sum(isinstance(child, ast.If) for child in ast.walk(node))
            return if_count
    raise AssertionError(f"{function_name} not found in {source_path}")


def test_execution_payload_mapping_is_not_a_compatibility_reexport_bucket() -> None:
    execution_root = SOURCE_ROOT / "execution"

    assert not (execution_root / "payload_mapping.py").exists()
    assert (execution_root / "payload_transport.py").exists()
    assert (execution_root / "contract_promotion.py").exists()
    assert (execution_root / "tool_interactions.py").exists()


def test_teamwork_snapshot_surface_is_split_by_responsibility() -> None:
    teamwork_root = SOURCE_ROOT / "teamwork"

    assert (teamwork_root / "team_api_transport.py").exists()
    assert (teamwork_root / "team_api_normalizers.py").exists()
    assert len((teamwork_root / "team_api_snapshot.py").read_text().splitlines()) < 430


def test_ralph_control_surface_is_split_by_responsibility() -> None:
    ralph_root = SOURCE_ROOT / "runtime" / "ralph"

    assert (ralph_root / "ralph_state.py").exists()
    assert (ralph_root / "ralph_prd.py").exists()
    assert (ralph_root / "ralph_team_handoff.py").exists()
    assert len((ralph_root / "ralph_control.py").read_text().splitlines()) < 430


def test_no_reexport_or_marker_init_files_remain() -> None:
    unnecessary_init_files: list[str] = []
    for init_path in SOURCE_ROOT.rglob("__init__.py"):
        if init_path == SOURCE_ROOT / "__init__.py":
            continue
        unnecessary_init_files.append(str(init_path.relative_to(REPO_ROOT)))

    assert unnecessary_init_files == []


def test_json_extraction_if_chains_use_msgspec_instead_of_tracking_lists() -> None:
    deleted_tracking_path = (
        SOURCE_ROOT / "adapter_types" / "type_contract" / "msgspec_tracking_contract_type.py"
    )
    renamed_tracking_path = (
        SOURCE_ROOT / "adapter_types" / "type_contract" / "tracking_contract_type.py"
    )

    assert not deleted_tracking_path.exists()
    assert not renamed_tracking_path.exists()

    json_loader_paths = [
        SOURCE_ROOT / "teamwork" / "team_api_transport.py",
        SOURCE_ROOT / "teamwork" / "team_snapshot.py",
        SOURCE_ROOT / "history" / "session_search.py",
    ]
    for loader_path in json_loader_paths:
        source_text = loader_path.read_text()
        assert "msgspec.convert" in source_text

    assert _function_if_count(
        SOURCE_ROOT / "teamwork" / "team_api_transport.py",
        "load_team_api_payload",
    ) < 6
    assert _function_if_count(
        SOURCE_ROOT / "teamwork" / "team_api_transport.py",
        "load_team_api_error_payload",
    ) < 6


def test_omx_task_quoting_is_shared() -> None:
    shared_quote_path = SOURCE_ROOT / "shared" / "utils" / "omx_task.py"
    ralph_control_text = (SOURCE_ROOT / "runtime" / "ralph" / "ralph_control.py").read_text()

    assert shared_quote_path.exists()
    assert "def quote_omx_task" in shared_quote_path.read_text()
    assert "def _quote_omx_task" not in ralph_control_text
