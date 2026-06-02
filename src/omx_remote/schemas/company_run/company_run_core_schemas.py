from pydantic import Field, model_validator

from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel
from omx_remote.shared.omx_enums.company_run_enums import (
    CompanyRunArtifactKind,
    CompanyRunRoleGroup,
)


class CompanyRunRosterSeat(StrictSchemaModel):
    """One company-run seat with bounded ownership and subagent policy."""

    seat_id: NonEmptyString
    group: CompanyRunRoleGroup
    agent: NonEmptyString
    responsibility: NonEmptyString
    artifact_path: NonEmptyString
    may_spawn_subagents: bool = False
    required: bool = True


class CompanyRunRoster(StrictSchemaModel):
    """Validated organization roster for a non-one-agent company-run."""

    seats: tuple[CompanyRunRosterSeat, ...]

    @model_validator(mode="after")
    def _validate_unique_seats(self) -> "CompanyRunRoster":
        """Validate roster seat identity.

        Returns:
            CompanyRunRoster: Validated roster instance.
        """
        seat_ids = [seat.seat_id for seat in self.seats]
        if len(seat_ids) != len(set(seat_ids)):
            raise ValueError("company-run roster seat_id values must be unique")
        return self

    def seats_for_group(
        self, group: CompanyRunRoleGroup
    ) -> tuple[CompanyRunRosterSeat, ...]:
        """Return seats in one company-run role group.

        Args:
            group [CompanyRunRoleGroup]: Group to select.

        Returns:
            tuple[CompanyRunRosterSeat, ...]: Seats in the group.
        """
        seats: tuple[CompanyRunRosterSeat, ...] = tuple(
            seat for seat in self.seats if seat.group == group
        )
        return seats

    def agent_names(self) -> tuple[str, ...]:
        """Return configured agent names represented in the roster.

        Returns:
            tuple[str, ...]: Agent names for every seat.
        """
        names: tuple[str, ...] = tuple(seat.agent for seat in self.seats)
        return names


class CompanyRunArtifactRecord(StrictSchemaModel):
    """One durable company-run artifact in the run-local index."""

    kind: CompanyRunArtifactKind
    path: NonEmptyString
    required: bool = True
    exists: bool = False
    size_bytes: int = Field(ge=0, default=0)
    sha256: NonEmptyString | None = None
    note: NonEmptyString | None = None


class CompanyRunArtifactIndex(StrictSchemaModel):
    """Public artifact index returned by CLI/MCP status readers."""

    run_id: NonEmptyString
    root_path: NonEmptyString
    artifact_paths: tuple[NonEmptyString, ...]
    artifacts: tuple[CompanyRunArtifactRecord, ...] = ()


class CompanyRunArtifactSummaryPayload(StrictSchemaModel):
    """Typed payload for the run-level company-run artifacts summary file."""

    artifact_index_path: NonEmptyString
    artifacts: tuple[NonEmptyString, ...]
