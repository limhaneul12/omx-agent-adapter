from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from schemas.common_schemas import NonEmptyString
from shared.omx_enums.execution_enums import ExecutionPayloadKind

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

    kind: Literal[ExecutionPayloadKind.MESSAGE]
    text: str


class ExecOutput(BaseModel):
    """Represents promoted plain-text execution output."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal[ExecutionPayloadKind.OUTPUT_TEXT]
    text: str


class ExecToolCall(BaseModel):
    """Represents a promoted tool-call event."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal[ExecutionPayloadKind.TOOL_CALL]
    tool_name: NonEmptyString
    call_id: NonEmptyString
    arguments: str


class ExecToolResult(BaseModel):
    """Represents a promoted tool-result event."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal[ExecutionPayloadKind.TOOL_RESULT]
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
    def _validate_state(self) -> "ToolInteraction":
        expected_state: ToolInteractionState = (
            "missing_result" if self.result is None else "completed"
        )
        if self.state != expected_state:
            raise ValueError(
                "tool interaction state must match result presence"
            )
        validated_interaction: ToolInteraction = self
        return validated_interaction


class ToolInteractionReport(BaseModel):
    """Represents grouped tool interactions plus anomaly buckets."""

    model_config = ConfigDict(extra="forbid")

    interactions: list[ToolInteraction]
    unmatched_results: list[ExecToolResult]
    duplicate_results: list[ExecToolResult]
    missing_result_calls: list[ExecToolCall]
    anomalies: list[ToolInteractionAnomaly]
