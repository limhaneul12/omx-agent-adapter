from pydantic import model_validator

from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel
from omx_remote.shared.omx_enums.agent_enums import AgentEffort


class CommandRuntimeOptions(StrictSchemaModel):
    """Per-invocation model/reasoning controls for command execution surfaces."""

    model: NonEmptyString | None = None
    reasoning_effort: AgentEffort | None = None
    madmax: bool = False

    @model_validator(mode="after")
    def _validate_non_empty_override(self) -> "CommandRuntimeOptions":
        """Require at least one runtime override when the object is present.

        Returns:
            CommandRuntimeOptions: Validated options.
        """
        if self.model is None and self.reasoning_effort is None and not self.madmax:
            raise ValueError("command runtime options require at least one override")
        return self
