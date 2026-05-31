from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel
from omx_remote.shared.omx_enums.teamwork_enums import (
    TeamProofLayerName,
    TeamProofLayerState,
)


class TeamProofLayerSummary(StrictSchemaModel):
    """Summarizes one evidence layer in a Team/Ralph execution wave."""

    name: TeamProofLayerName
    state: TeamProofLayerState
    summary: NonEmptyString
    source_names: tuple[NonEmptyString, ...] = ()
    blocking: bool
