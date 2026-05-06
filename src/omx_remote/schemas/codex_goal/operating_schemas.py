from omx_remote.schemas.codex_goal.lifecycle_schemas import (
    CodexGoalLifecycleRestoredState,
)
from omx_remote.schemas.common_schemas import (
    NonEmptyString,
    NonEmptyStrings,
    StrictSchemaModel,
)
from omx_remote.shared.omx_enums.codex_goal_enums import (
    CodexGoalOperatingAction,
    CodexGoalOperatingEvidenceSource,
    CodexGoalOperatingStage,
)


class CodexGoalEvidenceRequirement(StrictSchemaModel):
    """One observed or missing evidence source for agent-facing OMX operation."""

    source: CodexGoalOperatingEvidenceSource
    required: bool
    available: bool
    command: NonEmptyString | None = None
    summary: NonEmptyString


class CodexGoalOperatingDecisionRequest(StrictSchemaModel):
    """Request to recommend the next agent action from restored Goal lifecycle state."""

    restored_state: CodexGoalLifecycleRestoredState
    team_name: NonEmptyString


class CodexGoalOperatingDecisionResult(StrictSchemaModel):
    """Agent-facing next action and evidence map for operating OMX safely."""

    goal_id: NonEmptyString
    current_stage: CodexGoalOperatingStage
    next_action: CodexGoalOperatingAction
    safe_to_mutate: bool
    requires_review: bool
    available_evidence: NonEmptyStrings
    missing_evidence: NonEmptyStrings
    evidence_requirements: tuple[CodexGoalEvidenceRequirement, ...]
    recommended_commands: NonEmptyStrings
    review_blockers: NonEmptyStrings
    summary: NonEmptyString
