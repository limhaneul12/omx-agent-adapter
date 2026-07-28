from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

NonEmptyString = Annotated[str, Field(min_length=1)]
Sha256Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class StrictModel(BaseModel):
    """Shared immutable contract base for the public harness surface."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_enum_values=True,
        validate_default=True,
    )
