from typing import Literal

from pydantic import NonNegativeInt

from omx_remote.schemas.common_schemas import (
    NonEmptyString,
    StrictSchemaModel,
)
from omx_remote.shared.omx_enums.execution_enums import ExecutionPayloadKind


class ExecMessage(StrictSchemaModel):
    """Represents a promoted execution message event."""

    kind: Literal[ExecutionPayloadKind.MESSAGE]
    text: str


class ExecOutput(StrictSchemaModel):
    """Represents promoted plain-text execution output."""

    kind: Literal[ExecutionPayloadKind.OUTPUT_TEXT]
    text: str


class ExecCommandExecution(StrictSchemaModel):
    """Represents a promoted command-execution event."""

    kind: Literal[ExecutionPayloadKind.COMMAND_EXECUTION]
    command: NonEmptyString
    aggregated_output: str
    exit_code: int
    status: NonEmptyString


class ExecToolCall(StrictSchemaModel):
    """Represents a promoted tool-call event."""

    kind: Literal[ExecutionPayloadKind.TOOL_CALL]
    tool_name: NonEmptyString
    call_id: NonEmptyString
    arguments: str


class ExecToolResult(StrictSchemaModel):
    """Represents a promoted tool-result event."""

    kind: Literal[ExecutionPayloadKind.TOOL_RESULT]
    tool_name: NonEmptyString
    call_id: NonEmptyString
    text: str


class TurnUsage(StrictSchemaModel):
    """Represents stable token-usage metadata reported on turn completion."""

    input_tokens: NonNegativeInt
    cached_input_tokens: NonNegativeInt
    output_tokens: NonNegativeInt
    reasoning_output_tokens: NonNegativeInt
