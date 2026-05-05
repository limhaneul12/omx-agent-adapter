from typing import Annotated

from pydantic import BaseModel, ConfigDict, RootModel, StringConstraints

NonEmptyString = Annotated[str, StringConstraints(min_length=1)]


class StrictSchemaModel(BaseModel):
    """Base schema contract for strict named-field adapter-facing models."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_enum_values=True,
        validate_default=True,
    )


class StrictRootSchemaModel[RootValueT](RootModel[RootValueT]):
    """Strict base for root-value schema contracts."""

    model_config = ConfigDict(
        frozen=True,
        use_enum_values=True,
        validate_default=True,
    )
