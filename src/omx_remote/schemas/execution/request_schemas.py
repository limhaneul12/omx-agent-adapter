from omx_remote.schemas.common_schemas import (
    NonEmptyString,
    StrictSchemaModel,
)


class ExecRequest(StrictSchemaModel):
    """Represents a normalized execution request."""

    prompt: NonEmptyString
    cwd: NonEmptyString | None = None


class ExecutionEventDecodeRequest(StrictSchemaModel):
    """Represents the typed request boundary for execution event decoding."""

    payload: NonEmptyString
