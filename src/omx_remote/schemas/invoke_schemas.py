from omx_remote.schemas.common_schemas import StrictSchemaModel


class OmxCommandResult(StrictSchemaModel):
    """Represents the shared OMX command-result boundary."""

    exit_code: int
    stdout: str
    stderr: str
