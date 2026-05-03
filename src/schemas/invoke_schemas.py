from pydantic import BaseModel, ConfigDict


class OmxCommandResult(BaseModel):
    """Represents the shared OMX command-result boundary."""

    model_config = ConfigDict(extra="forbid")

    exit_code: int
    stdout: str
    stderr: str
