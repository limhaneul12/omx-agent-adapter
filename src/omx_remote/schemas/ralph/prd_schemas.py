from typing import Self

from pydantic import Field, model_validator

from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel
from omx_remote.shared.omx_enums.ralph_enums import RalphPrdContinuationPolicy


class RalphPrdArtifact(StrictSchemaModel):
    """Represents the minimum stable Ralph-owned PRD artifact contract."""

    objective: NonEmptyString
    scope: list[NonEmptyString] = Field(min_length=1)
    constraints: list[NonEmptyString]
    execution_plan: list[NonEmptyString] = Field(min_length=1)
    verification_expectations: list[NonEmptyString] = Field(min_length=1)
    requires_team_fanout: bool
    team_worker_count: int | None = Field(default=None, ge=1)
    continuation_policy: RalphPrdContinuationPolicy

    @model_validator(mode="after")
    def validate_team_worker_count(self) -> Self:
        if self.requires_team_fanout and self.team_worker_count is None:
            raise ValueError(
                "team_worker_count is required when requires_team_fanout is true."
            )

        if not self.requires_team_fanout and self.team_worker_count is not None:
            raise ValueError(
                "team_worker_count must be omitted when requires_team_fanout is false."
            )

        return self
