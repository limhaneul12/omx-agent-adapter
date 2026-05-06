from pathlib import Path


def test_runtime_concepts_live_under_classified_subpackages() -> None:
    runtime_root = Path("src/omx_remote/runtime")

    assert not (runtime_root / "runtime_snapshot.py").exists()
    assert not (runtime_root / "runtime_mode_status.py").exists()
    assert not (runtime_root / "runtime_mode_state.py").exists()
    assert not (runtime_root / "active_runtime_modes.py").exists()
    assert not (runtime_root / "codex_goal_runtime.py").exists()
    assert not (runtime_root / "codex_goal_supervisor.py").exists()
    assert not (runtime_root / "multi_operator.py").exists()
    assert not (runtime_root / "operator_loop.py").exists()
    assert not (runtime_root / "ralph_control.py").exists()
    assert not (runtime_root / "ultrawork_control.py").exists()

    assert (runtime_root / "status" / "runtime_snapshot.py").exists()
    assert (runtime_root / "status" / "runtime_mode_status.py").exists()
    assert (runtime_root / "status" / "runtime_mode_state.py").exists()
    assert (runtime_root / "status" / "active_runtime_modes.py").exists()
    assert (runtime_root / "goal" / "codex_goal_runtime.py").exists()
    assert (runtime_root / "goal" / "codex_goal_supervisor.py").exists()
    assert (runtime_root / "operators" / "multi_operator.py").exists()
    assert (runtime_root / "operators" / "operator_loop.py").exists()
    assert (runtime_root / "ralph" / "ralph_control.py").exists()
    assert (runtime_root / "ultrawork" / "ultrawork_control.py").exists()


def test_runtime_classified_import_surfaces_are_available() -> None:
    from omx_remote.runtime.goal.codex_goal_runtime import start_codex_goal
    from omx_remote.runtime.goal.codex_goal_supervisor import select_goal_delegation
    from omx_remote.runtime.operators.multi_operator import MultiOperatorRegistry
    from omx_remote.runtime.operators.operator_loop import operate_ralph_launch
    from omx_remote.runtime.ralph.ralph_state import RalphStateClassifier
    from omx_remote.runtime.status.runtime_mode_status import read_runtime_mode_status
    from omx_remote.runtime.status.runtime_snapshot import read_runtime_status
    from omx_remote.runtime.ultrawork.ultrawork_control import UltraworkStateClassifier

    assert start_codex_goal is not None
    assert select_goal_delegation is not None
    assert MultiOperatorRegistry is not None
    assert operate_ralph_launch is not None
    assert RalphStateClassifier is not None
    assert read_runtime_mode_status is not None
    assert read_runtime_status is not None
    assert UltraworkStateClassifier is not None
