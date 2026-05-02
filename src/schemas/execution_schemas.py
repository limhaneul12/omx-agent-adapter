from typing import Annotated, Literal

from pydantic import ConfigDict, StringConstraints, model_validator

from schemas.common_schemas import AdapterSchema

NonEmptyString = Annotated[str, StringConstraints(min_length=1)]
ToolInteractionState = Literal["completed", "missing_result"]


class ExecRequest(AdapterSchema):
    """Represents a normalized execution request."""

    model_config = ConfigDict(extra="forbid")

    prompt: NonEmptyString
    cwd: str | None = None


class ExecMessage(AdapterSchema):
    """Represents a promoted execution message event."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["message"]
    text: str


class ExecOutput(AdapterSchema):
    """Represents promoted plain-text execution output."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["output_text"]
    text: str


class ExecToolCall(AdapterSchema):
    """Represents a promoted tool-call event."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["tool_call"]
    tool_name: NonEmptyString
    call_id: NonEmptyString
    arguments: str


class ExecToolResult(AdapterSchema):
    """Represents a promoted tool-result event."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["tool_result"]
    tool_name: NonEmptyString
    call_id: NonEmptyString
    text: str


class ToolInteractionAnomaly(AdapterSchema):
    """Represents a normalized anomaly from tool interaction grouping."""

    model_config = ConfigDict(extra="forbid")

    category: Literal["unmatched_result", "duplicate_result", "missing_result"]
    related_call_id: NonEmptyString
    tool_name: NonEmptyString
    summary: NonEmptyString


class ToolInteraction(AdapterSchema):
    """Represents one tool call paired with its first matching result."""

    model_config = ConfigDict(extra="forbid")

    state: ToolInteractionState
    call: ExecToolCall
    result: ExecToolResult | None = None

    @model_validator(mode="after")
    def _set_state(self) -> "ToolInteraction":
        if self.result is None:
            self.state = "missing_result"
        else:
            self.state = "completed"
        return self


class ToolInteractionReport(AdapterSchema):
    """Represents grouped tool interactions plus anomaly buckets."""

    model_config = ConfigDict(extra="forbid")

    interactions: list[ToolInteraction]
    unmatched_results: list[ExecToolResult]
    duplicate_results: list[ExecToolResult]
    missing_result_calls: list[ExecToolCall]
    anomalies: list[ToolInteractionAnomaly]
