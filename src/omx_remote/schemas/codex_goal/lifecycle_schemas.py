from omx_remote.schemas.codex_goal.runtime_schemas import CodexGoalMirrorState
from omx_remote.schemas.common_schemas import (
    NonEmptyString,
    NonEmptyStrings,
    StrictSchemaModel,
)
from omx_remote.schemas.ralph.review_schemas import RalphPostTeamReviewResult
from omx_remote.shared.omx_enums.codex_goal_enums import (
    CodexGoalLifecycleAction,
    CodexGoalLifecycleTarget,
)


class CodexGoalLifecycleDecisionRequest(StrictSchemaModel):
    """Goal-owned request to decide close, follow-up, or human review after Ralph."""

    mirror_state: CodexGoalMirrorState
    ralph_review_result: RalphPostTeamReviewResult


class CodexGoalLifecycleDecisionResult(StrictSchemaModel):
    """Goal-facing lifecycle decision after Ralph post-Team review."""

    goal_id: NonEmptyString
    action: CodexGoalLifecycleAction
    next_target: CodexGoalLifecycleTarget
    ready_to_close: bool
    requires_follow_up_wave: bool
    requires_human_approval: bool
    follow_up_workers: NonEmptyStrings
    review_blockers: NonEmptyStrings
    summary: NonEmptyString
