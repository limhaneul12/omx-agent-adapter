from typing import Literal, NotRequired, Required, TypedDict

from omx_remote.shared.omx_enums.execution_enums import ExecutionEventKind


class ExecutionUsageTransportPayload(TypedDict, total=False):
    """Represents the stable observed token-usage subset on turn completion."""

    input_tokens: NotRequired[int]
    cached_input_tokens: NotRequired[int]
    output_tokens: NotRequired[int]
    reasoning_output_tokens: NotRequired[int]


class ExecutionThreadStartedTransportPayload(TypedDict):
    """Represents the stable transport subset for `thread.started` events."""

    type: Required[ExecutionEventKind]
    thread_id: Required[str]


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

    id: NotRequired[str]
    type: NotRequired[str]
    text: NotRequired[str]
    tool_name: NotRequired[str]
    call_id: NotRequired[str]
    arguments: NotRequired[str]
    command: NotRequired[str]
    aggregated_output: NotRequired[str]
    exit_code: NotRequired[int]
    status: NotRequired[str]


class ExecutionTurnCompletedTransportPayload(TypedDict):
    """Represents the stable transport subset for `turn.completed` events."""

    type: Required[ExecutionEventKind]
    usage: Required[ExecutionUsageTransportPayload]


class ExecutionItemCompletedTransportPayload(TypedDict):
    """Represents the stable transport subset for `item.completed` events."""

    type: Required[ExecutionEventKind]
    item: Required[ExecutionItemTransportPayload]


class ExecutionTransportPayload(TypedDict, total=False):
    """Represents the owned top-level execution transport subset before promotion."""

    type: NotRequired[str | None]
    text: NotRequired[str]
    item: NotRequired[ExecutionItemTransportPayload]
    tool_name: NotRequired[str]
    call_id: NotRequired[str]
    arguments: NotRequired[str]
    command: NotRequired[str]
    aggregated_output: NotRequired[str]
    exit_code: NotRequired[int]
    status: NotRequired[str]
    id: NotRequired[str]
    extra: NotRequired[object]
    kind: NotRequired[object]
    thread_id: NotRequired[str]
    usage: NotRequired[ExecutionUsageTransportPayload]


class ExecMessageNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for message promotion."""

    kind: Required[Literal["message"]]
    text: Required[str]


class ExecOutputNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for output-text promotion."""

    kind: Required[Literal["output_text"]]
    text: Required[str]


class ExecCommandExecutionNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for command-execution promotion."""

    kind: Required[Literal["command_execution"]]
    command: Required[str]
    aggregated_output: Required[str]
    exit_code: Required[int]
    status: Required[str]


class ExecToolCallNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for tool-call promotion."""

    kind: Required[Literal["tool_call"]]
    tool_name: Required[str]
    call_id: Required[str]
    arguments: Required[str]


class ExecToolResultNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for tool-result promotion."""

    kind: Required[Literal["tool_result"]]
    tool_name: Required[str]
    call_id: Required[str]
    text: Required[str]
