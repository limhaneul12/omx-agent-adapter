from pathlib import Path

from omx_remote.schemas.codex_goal.lifecycle_schemas import (
    CodexGoalLifecycleArtifactBundle,
    CodexGoalLifecycleRestoredState,
)
from omx_remote.shared.omx_enums.codex_goal_enums import (
    CodexGoalLifecycleRestoreTarget,
)
from omx_remote.shared.utils.json_file_store import json_file_stores


def resolve_goal_lifecycle_working_directory(working_directory: str | None = None) -> Path:
    """Resolves the workspace that owns durable Goal lifecycle artifacts.

    Args:
        working_directory [str | None]: Optional workspace path.

    Returns:
        Path: Resolved workspace path.
    """
    if working_directory is None:
        resolved_path: Path = Path.cwd().resolve()
    else:
        resolved_path = Path(working_directory).resolve()

    return resolved_path


def get_goal_lifecycle_artifact_path(
    goal_id: str,
    working_directory: str | None = None,
) -> Path:
    """Builds the durable artifact path for one Goal lifecycle bundle.

    Args:
        goal_id [str]: Goal identifier that owns the lifecycle bundle.
        working_directory [str | None]: Optional workspace path.

    Returns:
        Path: `.agent-remote` JSON artifact path for the Goal lifecycle bundle.
    """
    workspace_path: Path = resolve_goal_lifecycle_working_directory(working_directory)
    artifact_path: Path = (
        workspace_path / ".agent-remote" / "state" / "goal-lifecycle" / f"{goal_id}.json"
    )
    return artifact_path


def restore_target_from_bundle(
    bundle: CodexGoalLifecycleArtifactBundle,
) -> CodexGoalLifecycleRestoreTarget:
    """Selects the next resume target from available durable artifacts.

    Args:
        bundle [CodexGoalLifecycleArtifactBundle]: Restored lifecycle artifact bundle.

    Returns:
        CodexGoalLifecycleRestoreTarget: Next adapter surface to resume.
    """
    if bundle.lifecycle_decision is not None:
        target = CodexGoalLifecycleRestoreTarget(bundle.lifecycle_decision.next_target)
    elif bundle.ralph_review_result is not None:
        target = CodexGoalLifecycleRestoreTarget.GOAL_LIFECYCLE_DECISION
    elif bundle.aggregation_report is not None:
        target = CodexGoalLifecycleRestoreTarget.RALPH_POST_TEAM_REVIEW
    else:
        target = CodexGoalLifecycleRestoreTarget.TEAM_ADMIN_AGGREGATION

    return target


def build_restored_goal_lifecycle_summary(
    bundle: CodexGoalLifecycleArtifactBundle,
    next_resume_target: CodexGoalLifecycleRestoreTarget,
) -> str:
    """Builds a stable summary for restored Goal lifecycle state.

    Args:
        bundle [CodexGoalLifecycleArtifactBundle]: Restored lifecycle artifact bundle.
        next_resume_target [CodexGoalLifecycleRestoreTarget]: Target selected for resume.

    Returns:
        str: Agent-facing summary for the restored state.
    """
    summary: str = (
        f"Goal {bundle.goal_id} restored from durable lifecycle artifacts; "
        f"next resume target is {next_resume_target}."
    )
    return summary


class CodexGoalLifecycleArtifactStore:
    """Owns durable Goal lifecycle artifact bundle persistence for one workspace."""

    def __init__(self, working_directory: str | None = None) -> None:
        """Creates a workspace-bound Goal lifecycle artifact store.

        Args:
            working_directory [str | None]: Optional workspace path.
        """
        self.working_directory: Path = resolve_goal_lifecycle_working_directory(
            working_directory
        )

    def artifact_path_for_goal(self, goal_id: str) -> Path:
        """Builds the lifecycle bundle path for one Goal.

        Args:
            goal_id [str]: Goal identifier.

        Returns:
            Path: Goal lifecycle bundle JSON path.
        """
        artifact_path: Path = get_goal_lifecycle_artifact_path(
            goal_id,
            working_directory=str(self.working_directory),
        )
        return artifact_path

    def write_bundle(self, bundle: CodexGoalLifecycleArtifactBundle) -> Path:
        """Writes one durable Goal lifecycle artifact bundle.

        Args:
            bundle [CodexGoalLifecycleArtifactBundle]: Bundle to persist.

        Returns:
            Path: Path written by the artifact store.
        """
        artifact_path: Path = self.artifact_path_for_goal(bundle.goal_id)
        store = json_file_stores.for_path(artifact_path)
        store.write_model(bundle)
        written_path: Path = artifact_path
        return written_path

    def read_bundle(self, goal_id: str) -> CodexGoalLifecycleArtifactBundle:
        """Reads one durable Goal lifecycle artifact bundle.

        Args:
            goal_id [str]: Goal identifier.

        Returns:
            CodexGoalLifecycleArtifactBundle: Restored lifecycle artifact bundle.

        Raises:
            ValueError: Raised when the artifact is missing or malformed.
        """
        artifact_path: Path = self.artifact_path_for_goal(goal_id)
        store = json_file_stores.for_path(artifact_path)
        payload: dict[str, object] | None = store.read_object()
        if payload is None:
            raise ValueError(f"Missing Goal lifecycle artifact bundle for {goal_id}.")

        bundle: CodexGoalLifecycleArtifactBundle = (
            CodexGoalLifecycleArtifactBundle.model_validate(payload)
        )
        return bundle

    def restore_state(self, goal_id: str) -> CodexGoalLifecycleRestoredState:
        """Restores one Goal lifecycle bundle and selects the next resume target.

        Args:
            goal_id [str]: Goal identifier.

        Returns:
            CodexGoalLifecycleRestoredState: Restored lifecycle state and resume target.
        """
        bundle: CodexGoalLifecycleArtifactBundle = self.read_bundle(goal_id)
        next_resume_target: CodexGoalLifecycleRestoreTarget = restore_target_from_bundle(
            bundle
        )
        summary: str = build_restored_goal_lifecycle_summary(bundle, next_resume_target)
        restored_state: CodexGoalLifecycleRestoredState = (
            CodexGoalLifecycleRestoredState.model_validate(
                {
                    "artifact_path": str(self.artifact_path_for_goal(goal_id)),
                    "bundle": bundle,
                    "next_resume_target": next_resume_target,
                    "ready_to_resume": True,
                    "summary": summary,
                }
            )
        )
        return restored_state


def restore_goal_lifecycle_state(
    goal_id: str,
    working_directory: str | None = None,
) -> CodexGoalLifecycleRestoredState:
    """Restores durable Goal lifecycle artifacts for a workspace.

    Args:
        goal_id [str]: Goal identifier.
        working_directory [str | None]: Optional workspace path.

    Returns:
        CodexGoalLifecycleRestoredState: Restored lifecycle state and resume target.
    """
    store = CodexGoalLifecycleArtifactStore(working_directory)
    restored_state: CodexGoalLifecycleRestoredState = store.restore_state(goal_id)
    return restored_state
