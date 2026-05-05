from typing import Literal, TypedDict

from omx_remote.shared.omx_enums.execution_enums import (
    ExecutionEventKind,
    KnownExecutionEventType,
    PromotableExecutionPayloadType,
)

type KnownExecutionEventTypeSet = frozenset[KnownExecutionEventType]
type PromotableExecutionPayloadTypeSet = frozenset[PromotableExecutionPayloadType]
type ExecutionTransportPayloads = tuple[ExecutionTransportPayload, ...]


class ExecutionUsageTransportPayload(TypedDict, total=False):
    """Represents the stable observed token-usage subset on turn completion."""

    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    reasoning_output_tokens: int


class ExecutionThreadStartedTransportPayload(TypedDict):
    """Represents the stable transport subset for `thread.started` events."""

    type: ExecutionEventKind
    thread_id: str


class ExecutionAgentMessageItemTransportPayload(TypedDict):
    """Represents the stable observed `agent_message` execution-item subset."""

    id: str
    type: str
    text: str


class ExecutionCommandExecutionItemTransportPayload(TypedDict):
    """Represents the stable observed `command_execution` execution-item subset."""

    id: str
    type: str
    command: str
    aggregated_output: str
    exit_code: int
    status: str


class ExecutionItemTransportPayload(TypedDict, total=False):
    """Represents the stable mixed execution-item transport subset across known item kinds."""

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


class ExecutionTurnCompletedTransportPayload(TypedDict):
    """Represents the stable transport subset for `turn.completed` events."""

    type: ExecutionEventKind
    usage: ExecutionUsageTransportPayload


class ExecutionItemCompletedTransportPayload(TypedDict):
    """Represents the stable transport subset for `item.completed` events."""

    type: ExecutionEventKind
    item: ExecutionItemTransportPayload


class ExecutionTransportPayload(TypedDict, total=False):
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
    extra: object
    kind: object
    thread_id: str
    usage: ExecutionUsageTransportPayload


class ExecMessageNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for message promotion."""

    kind: Literal["message"]
    text: str


class ExecOutputNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for output-text promotion."""

    kind: Literal["output_text"]
    text: str


class ExecCommandExecutionNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for command-execution promotion."""

    kind: Literal["command_execution"]
    command: str
    aggregated_output: str
    exit_code: int
    status: str


class ExecToolCallNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for tool-call promotion."""

    kind: Literal["tool_call"]
    tool_name: str
    call_id: str
    arguments: str


class ExecToolResultNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for tool-result promotion."""

    kind: Literal["tool_result"]
    tool_name: str
    call_id: str
    text: str
