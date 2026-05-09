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



def test_cockpit_snapshot_surface_is_grouped_by_concept_packages() -> None:
    cockpit_root = SOURCE_ROOT / "runtime" / "cockpit"
    grouped_modules = [
        cockpit_root / "snapshot" / "reader.py",
        cockpit_root / "snapshot" / "builder.py",
        cockpit_root / "snapshot" / "lanes.py",
        cockpit_root / "snapshot" / "decisions.py",
        cockpit_root / "sources" / "status.py",
        cockpit_root / "sources" / "goal_mirror.py",
        cockpit_root / "sources" / "ultrawork.py",
        cockpit_root / "sources" / "github_pr_status.py",
        cockpit_root / "team_evidence" / "reader.py",
        cockpit_root / "team_evidence" / "summary.py",
        cockpit_root / "team_evidence" / "discovery.py",
    ]
    removed_flat_modules = [
        "cockpit_snapshot.py",
        "snapshot_reader.py",
        "snapshot_builder.py",
        "status_sources.py",
        "team_observation_reader.py",
        "lane_snapshots.py",
        "decisions.py",
        "ultrawork_observation.py",
        "goal_mirror_state.py",
        "team_summary.py",
        "linked_team_discovery.py",
        "github_pr_status.py",
    ]

    line_limited_modules = [
        module_path
        for module_path in grouped_modules
        if module_path.name != "github_pr_status.py"
    ]

    for module_path in grouped_modules:
        assert module_path.exists()

    for module_path in line_limited_modules:
        assert len(module_path.read_text().splitlines()) < 430

    for module_name in removed_flat_modules:
        assert not (cockpit_root / module_name).exists()

    assert list(cockpit_root.glob("*.py")) == []


def test_ultrawork_control_surface_is_split_by_responsibility() -> None:
    ultrawork_root = SOURCE_ROOT / "runtime" / "ultrawork"

    assert (ultrawork_root / "ultrawork_state_classifier.py").exists()
    assert len((ultrawork_root / "ultrawork_control.py").read_text().splitlines()) < 430


def test_runtime_classes_keep_small_cohesive_method_sets() -> None:
    inspected_paths = [
        SOURCE_ROOT / "runtime" / "ultrawork" / "ultrawork_state_classifier.py",
    ]
    for inspected_path in inspected_paths:
        module_tree = ast.parse(inspected_path.read_text(), filename=str(inspected_path))
        for node in module_tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            method_count = sum(
                isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef)
                for child in node.body
            )
            assert method_count <= 6, f"{inspected_path}:{node.name} has {method_count} methods"

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
