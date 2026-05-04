from typing import Required, TypedDict

from omx_remote.shared.omx_enums.execution_enums import ExecutionEventKind


class ExecutionUsageTransportPayload(TypedDict, total=False):
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    reasoning_output_tokens: int


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
    type: Required[ExecutionEventKind]
    usage: Required[ExecutionUsageTransportPayload]


class ExecutionItemCompletedTransportPayload(TypedDict):
    type: Required[ExecutionEventKind]
    item: Required[ExecutionItemTransportPayload]


class ExecutionTransportPayload(TypedDict, total=False):
    type: str | None
    text: object
    item: object
    tool_name: object
    call_id: object
    arguments: object
    command: object
    aggregated_output: object
    exit_code: object
    status: object
    id: object
    extra: object
    kind: object
    thread_id: str
    usage: ExecutionUsageTransportPayload


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
