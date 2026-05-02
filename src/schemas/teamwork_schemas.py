from pydantic import BaseModel, ConfigDict

from schemas.common_schemas import NonEmptyString


class TeamStatusRequest(BaseModel):
    """Represents the typed request boundary for team status reads."""

    model_config = ConfigDict(extra="forbid")

    team_name: NonEmptyString


class TeamAwaitRequest(BaseModel):
    """Represents the typed request boundary for team await reads."""

    model_config = ConfigDict(extra="forbid")

    team_name: NonEmptyString
