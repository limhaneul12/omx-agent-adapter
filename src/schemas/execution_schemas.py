from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from schemas.common_schemas import NonEmptyString

ToolInteractionState = Literal["completed", "missing_result"]
ExecutionAnomalyCategory = Literal[
    "unmatched_result",
    "duplicate_result",
    "missing_result",
]


class ExecRequest(BaseModel):
    """Represents a normalized execution request."""

    model_config = ConfigDict(extra="forbid")

    prompt: NonEmptyString
    cwd: NonEmptyString | None = None


class ExecutionEventDecodeRequest(BaseModel):
    """Represents the typed request boundary for execution event decoding."""

    model_config = ConfigDict(extra="forbid")

    payload: NonEmptyString


class ExecMessage(BaseModel):
    """Represents a promoted execution message event."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["message"]
    text: str


class ExecOutput(BaseModel):
    """Represents promoted plain-text execution output."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["output_text"]
    text: str


class ExecToolCall(BaseModel):
    """Represents a promoted tool-call event."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["tool_call"]
    tool_name: NonEmptyString
    call_id: NonEmptyString
    arguments: str


class ExecToolResult(BaseModel):
    """Represents a promoted tool-result event."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["tool_result"]
    tool_name: NonEmptyString
    call_id: NonEmptyString
    text: str


class ToolInteractionAnomaly(BaseModel):
    """Represents a normalized anomaly from tool interaction grouping."""

    model_config = ConfigDict(extra="forbid")

    category: ExecutionAnomalyCategory
    related_call_id: NonEmptyString
    tool_name: NonEmptyString
    summary: NonEmptyString


class ToolInteraction(BaseModel):
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


class ToolInteractionReport(BaseModel):
    """Represents grouped tool interactions plus anomaly buckets."""

    model_config = ConfigDict(extra="forbid")

    interactions: list[ToolInteraction]
    unmatched_results: list[ExecToolResult]
    duplicate_results: list[ExecToolResult]
    missing_result_calls: list[ExecToolCall]
    anomalies: list[ToolInteractionAnomaly]
