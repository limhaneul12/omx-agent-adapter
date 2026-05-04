from typing import NotRequired, Required, TypedDict

from omx_remote.shared.omx_enums.execution_enums import ExecutionEventKind


class ExecutionUsageTransportPayload(TypedDict, total=False):
    input_tokens: NotRequired[int]
    cached_input_tokens: NotRequired[int]
    output_tokens: NotRequired[int]
    reasoning_output_tokens: NotRequired[int]


class ExecutionThreadStartedTransportPayload(TypedDict):
    type: Required[ExecutionEventKind]
    thread_id: Required[str]


class ExecutionAgentMessageItemTransportPayload(TypedDict):
    id: str
    type: str
    text: str


class ExecutionCommandExecutionItemTransportPayload(TypedDict):
    id: str
    type: str
    command: str
    aggregated_output: str
    exit_code: int
    status: str


class ExecutionItemTransportPayload(TypedDict, total=False):
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
    type: Required[ExecutionEventKind]
    usage: Required[ExecutionUsageTransportPayload]


class ExecutionItemCompletedTransportPayload(TypedDict):
    type: Required[ExecutionEventKind]
    item: Required[ExecutionItemTransportPayload]


class ExecutionTransportPayload(TypedDict, total=False):
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
    kind: Required[object]
    text: Required[object]


class ExecOutputNormalizedPayload(TypedDict):
    kind: Required[object]
    text: Required[object]


class ExecCommandExecutionNormalizedPayload(TypedDict):
    kind: Required[object]
    command: Required[object]
    aggregated_output: Required[object]
    exit_code: Required[object]
    status: Required[object]


class ExecToolCallNormalizedPayload(TypedDict):
    kind: Required[object]
    tool_name: Required[object]
    call_id: Required[object]
    arguments: Required[object]


class ExecToolResultNormalizedPayload(TypedDict):
    kind: Required[object]
    tool_name: Required[object]
    call_id: Required[object]
    text: Required[object]
