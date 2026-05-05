from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

NonEmptyString = Annotated[str, StringConstraints(min_length=1)]


class StrictSchemaModel(BaseModel):
    """Base schema contract for strict adapter-facing schemas (forbid extras)."""

    model_config = ConfigDict(extra="forbid")
