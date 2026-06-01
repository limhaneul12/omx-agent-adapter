from pydantic import Field

from omx_remote.schemas.common_schemas import (
    NonEmptyString,
    NonEmptyStrings,
    StrictSchemaModel,
)


class PrdValidationCaptureResult(StrictSchemaModel):
    """Represents one validated PRD capture operation."""

    valid: bool
    input_path: NonEmptyString
    output_path: NonEmptyString | None = None
    objective: NonEmptyString
    requires_team_fanout: bool
    team_worker_count: int | None = Field(default=None, ge=1)
    assignment_worker_ids: NonEmptyStrings = ()
