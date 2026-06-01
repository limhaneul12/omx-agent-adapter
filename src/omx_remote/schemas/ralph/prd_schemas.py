from typing import Self

from pydantic import Field, model_validator

from omx_remote.schemas.common_schemas import (
    NonEmptyString,
    NonEmptyStrings,
    StrictRootSchemaModel,
    StrictSchemaModel,
)
from omx_remote.shared.omx_enums.ralph_enums import (
    RalphPrdContinuationPolicy,
    TeamAdminAggregationPolicy,
    TeamAdminCompletionPolicy,
    TeamAdminMergePolicy,
    TeamWorkerAuthorizationPolicy,
)


class TeamWorkerAuthorizationScope(StrictSchemaModel):
    """Allowed and escalated actions for one Team worker assignment."""

    allowed_commands: NonEmptyStrings = ()
    forbidden_commands: NonEmptyStrings = ()
    requires_human_for: NonEmptyStrings = ()
    requires_llm_review_for: NonEmptyStrings = ()


class TeamWorkerAssignment(StrictSchemaModel):
    """Ralph-owned lane assignment for one Team worker."""

    worker_id: NonEmptyString
    lane_name: NonEmptyString
    objective: NonEmptyString
    owned_files: NonEmptyStrings = Field(min_length=1)
    read_only_context_files: NonEmptyStrings = ()
    forbidden_files: NonEmptyStrings = ()
    tdd_steps: NonEmptyStrings = Field(min_length=1)
    verification_commands: NonEmptyStrings = Field(min_length=1)
    handoff_summary_required: NonEmptyString
    authorization_policy: TeamWorkerAuthorizationPolicy
    authorization_scope: TeamWorkerAuthorizationScope


class RalphTeamDistributionPlan(
    StrictRootSchemaModel[tuple[TeamWorkerAssignment, ...]]
):
    """Root collection of Ralph-owned Team worker assignments."""

    @model_validator(mode="after")
    def validate_unique_worker_and_file_ownership(self) -> Self:
        """Handles validate unique worker and file ownership.

        Returns:
            Self: Function return value.
        """
        if not self.root:
            raise ValueError("Ralph Team distribution plan must contain assignments.")

        seen_workers: set[str] = set()
        seen_owned_files: dict[str, str] = {}
        duplicate_files: list[str] = []

        for assignment in self.root:
            if assignment.worker_id in seen_workers:
                raise ValueError(f"duplicate worker_id: {assignment.worker_id}")
            seen_workers.add(assignment.worker_id)

            for owned_file in assignment.owned_files:
                previous_owner = seen_owned_files.get(owned_file)
                if previous_owner is not None:
                    duplicate_files.append(
                        f"{owned_file} ({previous_owner}, {assignment.worker_id})"
                    )
                    continue
                seen_owned_files[owned_file] = assignment.worker_id

        if duplicate_files:
            duplicate_summary: str = ", ".join(duplicate_files)
            raise ValueError(
                f"duplicate owned_files across workers: {duplicate_summary}"
            )

        return self


class TeamAdminAggregationContract(StrictSchemaModel):
    """Ralph-owned Team Admin result aggregation and review contract."""

    admin_id: NonEmptyString
    aggregation_policy: TeamAdminAggregationPolicy
    merge_policy: TeamAdminMergePolicy
    completion_policy: TeamAdminCompletionPolicy
    requires_human_for: NonEmptyStrings = Field(min_length=1)
    requires_llm_review_for: NonEmptyStrings = Field(min_length=1)
    final_report_required: bool


class RalphPrdArtifact(StrictSchemaModel):
    """Represents the minimum stable Ralph-owned PRD artifact contract."""

    objective: NonEmptyString
    scope: NonEmptyStrings = Field(min_length=1)
    constraints: NonEmptyStrings
    execution_plan: NonEmptyStrings = Field(min_length=1)
    verification_expectations: NonEmptyStrings = Field(min_length=1)
    requires_team_fanout: bool
    team_worker_count: int | None = Field(default=None, ge=1)
    continuation_policy: RalphPrdContinuationPolicy
    team_worker_assignments: tuple[TeamWorkerAssignment, ...] | None = None
    team_admin: TeamAdminAggregationContract | None = None

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

        if self.requires_team_fanout and self.team_worker_assignments is None:
            raise ValueError(
                "Team worker assignments are required when requires_team_fanout is true."
            )

        if self.requires_team_fanout and self.team_admin is None:
            raise ValueError(
                "team_admin is required when requires_team_fanout is true."
            )

        if self.team_worker_assignments is not None:
            RalphTeamDistributionPlan(root=self.team_worker_assignments)

        if self.requires_team_fanout and self.team_worker_assignments is not None:
            assignment_count: int = len(self.team_worker_assignments)
            if assignment_count != self.team_worker_count:
                raise ValueError(
                    "team_worker_assignments length must match team_worker_count."
                )

        if not self.requires_team_fanout and self.team_worker_assignments is not None:
            raise ValueError(
                "team_worker_assignments must be omitted when requires_team_fanout is false."
            )

        if not self.requires_team_fanout and self.team_admin is not None:
            raise ValueError(
                "team_admin must be omitted when requires_team_fanout is false."
            )

        return self
