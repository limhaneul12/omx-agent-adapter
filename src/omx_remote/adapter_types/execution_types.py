from typing import Literal

import msgspec
from typing_extensions import TypedDict

from omx_remote.adapter_types.json_types import JsonValue
from omx_remote.schemas.execution.event_schemas import (
    ExecCommandExecution,
    ExecMessage,
    ExecOutput,
    ExecToolCall,
    ExecToolResult,
)
from omx_remote.shared.omx_enums.execution_enums import (
    ExecutionEventKind,
    ExecutionPayloadKind,
    KnownExecutionEventType,
    PromotableExecutionPayloadType,
)

type KnownExecutionEventTypeSet = frozenset[KnownExecutionEventType]
type PromotableExecutionPayloadTypeSet = frozenset[PromotableExecutionPayloadType]
type ExecutionPayload = ExecutionTransportPayload
type ExecutionContract = (
    ExecMessage
    | ExecOutput
    | ExecCommandExecution
    | ExecToolCall
    | ExecToolResult
)
type RoutedExecutionPayload = ExecutionContract | ExecutionPayload
type ExecutionTransportPayloads = tuple[ExecutionTransportPayload, ...]


class ExecutionUsageTransportPayload(TypedDict, total=False, closed=True):
    """Represents the stable observed token-usage subset on turn completion."""

    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    reasoning_output_tokens: int


class ExecutionThreadStartedTransportPayload(TypedDict, closed=True):
    """Represents the stable transport subset for `thread.started` events."""

    type: ExecutionEventKind
    thread_id: str


class ExecutionAgentMessageItemTransportPayload(TypedDict, closed=True):
    """Represents the stable observed `agent_message` execution-item subset."""

    id: str
    type: str
    text: str


class ExecutionCommandExecutionItemTransportPayload(
    TypedDict,
    closed=True,
):
    """Represents the stable observed `command_execution` execution-item subset."""

    id: str
    type: str
    command: str
    aggregated_output: str
    exit_code: int
    status: str


class ExecutionItemTransportPayload(TypedDict, total=False, extra_items=JsonValue):
    """Represents the mixed execution-item subset with raw extras preserved."""

    id: str
    type: str
    text: str
    tool_name: str
    call_id: str
    arguments: str
    command: str
    aggregated_output: str
    exit_code: int
    status: str


class ExecutionTurnCompletedTransportPayload(TypedDict, closed=True):
    """Represents the stable transport subset for `turn.completed` events."""

    type: ExecutionEventKind
    usage: ExecutionUsageTransportPayload


class ExecutionItemCompletedTransportPayload(TypedDict, closed=True):
    """Represents the stable transport subset for `item.completed` events."""

    type: ExecutionEventKind
    item: ExecutionItemTransportPayload


# The upstream `extra` envelope is diagnostic metadata, so this leaf keeps
# JSON-shaped raw values while the field itself is narrowed to a mapping.
class ExecutionExtraTransportPayload(TypedDict, total=False, extra_items=JsonValue):
    """Represents raw upstream diagnostic metadata attached to execution events."""


class ExecutionTransportPayload(TypedDict, total=False, extra_items=JsonValue):
    """Represents the owned top-level execution transport subset before promotion."""

    type: str | None
    text: str
    item: ExecutionItemTransportPayload
    tool_name: str
    call_id: str
    arguments: str
    command: str
    aggregated_output: str
    exit_code: int
    status: str
    id: str
    extra: ExecutionExtraTransportPayload
    kind: str
    thread_id: str
    usage: ExecutionUsageTransportPayload


class ExecutionUsageSpec(msgspec.Struct, omit_defaults=True):
    """Represents the msgspec field contract for execution usage payloads."""

    input_tokens: int | None = None
    cached_input_tokens: int | None = None
    output_tokens: int | None = None
    reasoning_output_tokens: int | None = None


class ExecutionItemSpec(msgspec.Struct, omit_defaults=True):
    """Represents the msgspec field contract for execution item payloads."""

    id: str | None = None
    type: str | None = None
    text: str | None = None
    tool_name: str | None = None
    call_id: str | None = None
    arguments: str | None = None
    command: str | None = None
    aggregated_output: str | None = None
    exit_code: int | None = None
    status: str | None = None


class ExecutionTransportSpec(msgspec.Struct, omit_defaults=True):
    """Represents the msgspec field contract for top-level execution payloads."""

    type: str | None = None
    text: str | None = None
    item: ExecutionItemTransportPayload | None = None
    tool_name: str | None = None
    call_id: str | None = None
    arguments: str | None = None
    command: str | None = None
    aggregated_output: str | None = None
    exit_code: int | None = None
    status: str | None = None
    id: str | None = None
    extra: ExecutionExtraTransportPayload | None = None
    kind: str | None = None
    thread_id: str | None = None
    usage: ExecutionUsageTransportPayload | None = None


class ExecMessageNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for message promotion."""

    kind: Literal[ExecutionPayloadKind.MESSAGE]
    text: str


class ExecOutputNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for output-text promotion."""

    kind: Literal[ExecutionPayloadKind.OUTPUT_TEXT]
    text: str


class ExecCommandExecutionNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for command-execution promotion."""

    kind: Literal[ExecutionPayloadKind.COMMAND_EXECUTION]
    command: str
    aggregated_output: str
    exit_code: int
    status: str


class ExecToolCallNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for tool-call promotion."""

    kind: Literal[ExecutionPayloadKind.TOOL_CALL]
    tool_name: str
    call_id: str
    arguments: str


class ExecToolResultNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for tool-result promotion."""

    kind: Literal[ExecutionPayloadKind.TOOL_RESULT]
    tool_name: str
    call_id: str
    text: str
