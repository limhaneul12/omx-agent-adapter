from typing import Self

from pydantic import Field, model_validator

from omx_remote.schemas.codex_goal.runtime_schemas import (
    CodexGoalMirrorState,
    CodexGoalReviewPolicy,
)
from omx_remote.schemas.common_schemas import (
    NonEmptyString,
    NonEmptyStrings,
    StrictSchemaModel,
)
from omx_remote.schemas.multi_operator.snapshot_schemas import MultiOperatorSnapshot
from omx_remote.schemas.operator.action_schemas import OperatorActionResult
from omx_remote.schemas.ralph.prd_schemas import RalphPrdArtifact
from omx_remote.shared.omx_enums.codex_goal_enums import (
    CodexGoalSource,
    CodexGoalStatus,
    GoalDelegationDispatchAction,
    GoalDelegationDispatchStatus,
    GoalDelegationTarget,
)


class CodexGoalCapabilitySnapshot(StrictSchemaModel):
    """Represents the verified subset of Codex Goal capability evidence."""

    feature_flag_listed: bool
    feature_flag_enabled: bool
    goal_json_surface_verified: bool
    capability_summary: NonEmptyString


class CodexGoalSnapshot(StrictSchemaModel):
    """Represents one adapter-owned snapshot of a top-level goal."""

    goal_id: NonEmptyString
    objective_text: NonEmptyString
    status: CodexGoalStatus
    source: CodexGoalSource
    capability: CodexGoalCapabilitySnapshot
    tracked_flow_ids: NonEmptyStrings = ()
    active_flow_ids: NonEmptyStrings = ()
    open_blockers: NonEmptyStrings = ()


class GoalExecutionPolicy(StrictSchemaModel):
    """Represents the allowed supervisor choices for one goal."""

    allow_goal_standalone: bool = True
    allow_ralph_pipeline: bool = True
    allow_direct_exec: bool = True
    ralph_must_prepare_team_work: bool = True
    prefer_observe_when_active_flow_exists: bool = True
    prds_require_review_before_execution: bool = False


class GoalDelegationDecision(StrictSchemaModel):
    """Represents one typed next-step decision for a goal."""

    goal_id: NonEmptyString
    selected_target: GoalDelegationTarget
    reason: NonEmptyString
    requires_prd_refresh: bool = False
    requires_prd_review: bool = False
    requires_team_fanout: bool = False
    team_worker_count: int | None = Field(default=None, ge=1)
    can_finish_without_team: bool = False

    @model_validator(mode="after")
    def validate_team_worker_count(self) -> Self:
        """Handles validate team worker count.
        
        Returns:
            Self: Function return value.
        """
        if self.requires_team_fanout and self.team_worker_count is None:
            raise ValueError(
                "team_worker_count is required when requires_team_fanout is true."
            )

        if not self.requires_team_fanout and self.team_worker_count is not None:
            raise ValueError(
                "team_worker_count must be omitted when requires_team_fanout is false."
            )

        return self


class GoalDelegationDispatchResult(StrictSchemaModel):
    """Represents one typed attempt to bridge a goal decision into Ralph operator work."""

    goal_id: NonEmptyString
    selected_target: GoalDelegationTarget
    dispatch_status: GoalDelegationDispatchStatus
    dispatched_action: GoalDelegationDispatchAction = GoalDelegationDispatchAction.NONE
    blocker_reason: NonEmptyString | None = None
    operator_result: OperatorActionResult | None = None


class GoalPrdAuthoringPromptRequest(StrictSchemaModel):
    """Represents the typed prompt contract for Goal-scoped PRD authoring."""

    goal_id: NonEmptyString
    goal_objective_text: NonEmptyString
    source_paths: NonEmptyStrings = Field(min_length=1)
    requested_slice: NonEmptyString
    constraints: NonEmptyStrings
    verification_expectations: NonEmptyStrings = Field(min_length=1)
    review_policy: CodexGoalReviewPolicy
    team_worker_count: int | None = Field(ge=1)


class GoalPrdAuthoringPromptResult(StrictSchemaModel):
    """Represents one prepared Goal-scoped PRD authoring prompt."""

    mirror_state: CodexGoalMirrorState
    prompt_request: GoalPrdAuthoringPromptRequest
    prompt: NonEmptyString


class GoalToRalphHandoffPromptRequest(GoalPrdAuthoringPromptRequest):
    """Legacy request name for the Goal-scoped PRD authoring prompt."""


class GoalToRalphHandoffPromptResult(StrictSchemaModel):
    """Legacy result name for the Goal-scoped PRD authoring prompt."""

    mirror_state: CodexGoalMirrorState
    prompt_request: GoalToRalphHandoffPromptRequest
    prompt: NonEmptyString


class CodexGoalAdvanceRequest(StrictSchemaModel):
    """Represents one typed request to advance a tracked native Goal through supervisor selection and dispatch."""

    capability: CodexGoalCapabilitySnapshot
    multi_operator_snapshot: MultiOperatorSnapshot
    objective_is_already_structured: bool = False
    execution_policy: GoalExecutionPolicy = Field(default_factory=GoalExecutionPolicy)
    ralph_prd_artifact: RalphPrdArtifact | None = None
    force_cleanup: bool = False
    allow_non_tty: bool = False


class CodexGoalAdvanceResult(StrictSchemaModel):
    """Represents one typed end-to-end advance result for a tracked native Goal."""

    mirror_state: CodexGoalMirrorState
    goal_snapshot: CodexGoalSnapshot
    execution_policy: GoalExecutionPolicy
    decision: GoalDelegationDecision
    dispatch_result: GoalDelegationDispatchResult
