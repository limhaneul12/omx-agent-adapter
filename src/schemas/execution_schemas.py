from typing import Annotated, Literal

from pydantic import ConfigDict, StringConstraints

from schemas.common_schemas import AdapterSchema

NonEmptyString = Annotated[str, StringConstraints(min_length=1)]


class ExecRequest(AdapterSchema):
    model_config = ConfigDict(extra="forbid")

    prompt: NonEmptyString
    cwd: str | None = None


class ExecMessage(AdapterSchema):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["message"]
    text: str


class ExecOutput(AdapterSchema):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["output_text"]
    text: str


class ExecToolCall(AdapterSchema):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["tool_call"]
    tool_name: NonEmptyString
    call_id: NonEmptyString
    arguments: str


class ExecToolResult(AdapterSchema):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["tool_result"]
    tool_name: NonEmptyString
    call_id: NonEmptyString
    text: str


class ToolInteractionAnomaly(AdapterSchema):
    model_config = ConfigDict(extra="forbid")

    category: Literal["unmatched_result", "duplicate_result", "missing_result"]
    related_call_id: NonEmptyString
    tool_name: NonEmptyString


class ToolInteraction(AdapterSchema):
    model_config = ConfigDict(extra="forbid")

    call: ExecToolCall
    result: ExecToolResult | None = None


class ToolInteractionReport(AdapterSchema):
    model_config = ConfigDict(extra="forbid")

    interactions: list[ToolInteraction]
    unmatched_results: list[ExecToolResult]
    duplicate_results: list[ExecToolResult]
    missing_result_calls: list[ExecToolCall]
    anomalies: list[ToolInteractionAnomaly]
