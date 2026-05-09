from omx_remote.runtime.goal.codex_goal_runtime import CodexGoalMirrorStateStore
from omx_remote.schemas.codex_goal.runtime_schemas import CodexGoalMirrorState


def _read_optional_goal_mirror_state(repo_root: str) -> CodexGoalMirrorState | None:
    """Read Goal mirror state when present, otherwise return absent state.

    Args:
        repo_root [str]: Workspace root whose Goal mirror should be read.

    Returns:
        CodexGoalMirrorState | None: Refreshed Goal mirror state or ``None`` when missing/invalid.
    """
    store = CodexGoalMirrorStateStore(repo_root)
    try:
        goal_mirror_state: CodexGoalMirrorState = store.read_status()
    except ValueError:
        missing_goal_mirror_state: CodexGoalMirrorState | None = None
        return missing_goal_mirror_state

    return goal_mirror_state
