from typing import Self

from pydantic import model_validator

from omx_remote.schemas.codex_goal.runtime_schemas import CodexGoalMirrorState
from omx_remote.schemas.common_schemas import (
    NonEmptyString,
    NonEmptyStrings,
    StrictSchemaModel,
)
from omx_remote.schemas.ralph.review_schemas import RalphPostTeamReviewResult
from omx_remote.schemas.teamwork.admin_aggregation_schemas import (
    TeamAdminAggregationReport,
)
from omx_remote.shared.omx_enums.codex_goal_enums import (
    CodexGoalLifecycleAction,
    CodexGoalLifecycleRestoreTarget,
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


class CodexGoalLifecycleArtifactBundle(StrictSchemaModel):
    """Durable Goal lifecycle artifact bundle across Team Admin and Ralph stages."""

    goal_id: NonEmptyString
    mirror_state: CodexGoalMirrorState
    aggregation_report: TeamAdminAggregationReport | None = None
    ralph_review_result: RalphPostTeamReviewResult | None = None
    lifecycle_decision: CodexGoalLifecycleDecisionResult | None = None

    @model_validator(mode="after")
    def validate_goal_identity(self) -> Self:
        """Validates goal identity consistency across bundled artifacts.

        Returns:
            Self: Validated artifact bundle.
        """
        if self.mirror_state.goal_id != self.goal_id:
            raise ValueError("mirror_state goal_id must match bundle goal_id.")

        if (
            self.lifecycle_decision is not None
            and self.lifecycle_decision.goal_id != self.goal_id
        ):
            raise ValueError("lifecycle_decision goal_id must match bundle goal_id.")

        validated_bundle: Self = self
        return validated_bundle


class CodexGoalLifecycleRestoredState(StrictSchemaModel):
    """Restored durable Goal lifecycle state and the next resume target."""

    artifact_path: NonEmptyString
    bundle: CodexGoalLifecycleArtifactBundle
    next_resume_target: CodexGoalLifecycleRestoreTarget
    ready_to_resume: bool
    summary: NonEmptyString
