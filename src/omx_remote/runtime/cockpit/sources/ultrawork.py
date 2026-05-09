from pathlib import Path

from omx_remote.runtime.ultrawork.ultrawork_control import (
    UltraworkStateClassifier,
    get_ultrawork_state_root,
    list_ultrawork_state_paths,
)
from omx_remote.shared.omx_enums.ultrawork_enums import UltraworkStateClassification
from omx_remote.shared.utils.json_file_store import json_file_stores


def _read_ultrawork_state(
    repo_root: Path,
) -> tuple[UltraworkStateClassification, tuple[str, ...]]:
    """Read current Ultrawork state classification from workspace artifacts.

    Args:
        repo_root [Path]: Workspace root whose `.omx/state` directory should be inspected.

    Returns:
        tuple[UltraworkStateClassification, tuple[str, ...]]: State classification and warnings.
    """
    existing_state_paths: list[Path] = list_ultrawork_state_paths(repo_root)
    if not existing_state_paths:
        clean_state: tuple[UltraworkStateClassification, tuple[str, ...]] = (
            UltraworkStateClassification.CLEAN,
            (),
        )
        return clean_state

    state_root: Path = get_ultrawork_state_root(repo_root)
    ultrawork_state_path: Path = state_root / "ultrawork-state.json"
    if not ultrawork_state_path.exists():
        joined_paths: str = ", ".join(str(path) for path in existing_state_paths)
        stale_state: tuple[UltraworkStateClassification, tuple[str, ...]] = (
            UltraworkStateClassification.STALE,
            (f"Known Ultrawork state files without canonical state: {joined_paths}",),
        )
        return stale_state

    state_store = json_file_stores.for_path(ultrawork_state_path)
    state_payload: dict[str, object] | None = state_store.read_object()
    if state_payload is None:
        invalid_state: tuple[UltraworkStateClassification, tuple[str, ...]] = (
            UltraworkStateClassification.INVALID,
            (f"Ultrawork state file is present but unreadable: {ultrawork_state_path}",),
        )
        return invalid_state

    classification: UltraworkStateClassification = UltraworkStateClassifier.classify_state_snapshot(
        state_payload
    )
    classified_state: tuple[UltraworkStateClassification, tuple[str, ...]] = (
        classification,
        (f"Ultrawork state path: {ultrawork_state_path}",),
    )
    return classified_state
