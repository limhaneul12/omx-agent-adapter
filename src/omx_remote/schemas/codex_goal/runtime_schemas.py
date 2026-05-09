from pydantic import Field, model_validator

from omx_remote.schemas.common_schemas import (
    NonEmptyString,
    NonEmptyStrings,
    StrictSchemaModel,
)
from omx_remote.shared.omx_enums.codex_goal_enums import (
    CodexGoalExecutionShape,
    CodexGoalHandoffState,
    CodexGoalMirrorSource,
    CodexGoalReviewPolicy,
    CodexGoalSpawnStatus,
    CodexGoalTrackingState,
)


class CodexGoalLaunchRequest(StrictSchemaModel):
    """Represents the typed request boundary for native Codex Goal launch."""

    objective_text: NonEmptyString
    execution_shape: CodexGoalExecutionShape = CodexGoalExecutionShape.GOAL_ONLY
    review_policy: CodexGoalReviewPolicy = CodexGoalReviewPolicy.CONTINUE_AUTOMATICALLY
    team_worker_count: int | None = Field(default=None, ge=1)
    working_directory: NonEmptyString | None = None

    @model_validator(mode="after")
    def validate_team_worker_count(self) -> "CodexGoalLaunchRequest":
        """Handles validate team worker count.
        
        Returns:
            'CodexGoalLaunchRequest': Function return value.
        """
        if (
            self.execution_shape == CodexGoalExecutionShape.GOAL_ONLY
            and self.team_worker_count is not None
        ):
            raise ValueError(
                "team_worker_count must be omitted when execution_shape is goal_only."
            )

        validated_request: CodexGoalLaunchRequest = self
        return validated_request


class CodexGoalSpawnResult(StrictSchemaModel):
    """Represents the adapter-owned spawn boundary for one Codex Goal session."""

    session_locator: NonEmptyString
    process_id: int | None = Field(default=None, ge=1)
    spawn_status: CodexGoalSpawnStatus
    slash_command_written: bool
    error_text: NonEmptyString | None = None


class CodexGoalMirrorState(StrictSchemaModel):
    """Represents one adapter-owned mirror state for a native Codex Goal session."""

    goal_id: NonEmptyString
    objective_text: NonEmptyString
    source: CodexGoalMirrorSource
    execution_shape: CodexGoalExecutionShape
    review_policy: CodexGoalReviewPolicy
    team_worker_count: int | None = Field(default=None, ge=1)
    linked_team_names: NonEmptyStrings = ()
    working_directory: NonEmptyString
    codex_command: NonEmptyStrings = Field(min_length=1)
    session_locator: NonEmptyString
    process_id: int | None = Field(default=None, ge=1)
    launched_at: NonEmptyString
    handoff_state: CodexGoalHandoffState
    tracking_state: CodexGoalTrackingState

    @model_validator(mode="after")
    def validate_team_worker_count(self) -> "CodexGoalMirrorState":
        """Handles validate team worker count.
        
        Returns:
            'CodexGoalMirrorState': Function return value.
        """
        if (
            self.execution_shape == CodexGoalExecutionShape.GOAL_ONLY
            and self.team_worker_count is not None
        ):
            raise ValueError(
                "team_worker_count must be omitted when execution_shape is goal_only."
            )

        validated_state: CodexGoalMirrorState = self
        return validated_state


class CodexGoalLaunchResult(StrictSchemaModel):
    """Represents the typed public result for one native Codex Goal launch."""

    mirror_state: CodexGoalMirrorState
    spawn_result: CodexGoalSpawnResult
    slash_command_injected: bool
    warnings: NonEmptyStrings = ()
