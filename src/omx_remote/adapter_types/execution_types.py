from typing import Required, TypedDict


class ExecutionUsageTransportPayload(TypedDict, total=False):
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    reasoning_output_tokens: int


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
    command: str
    aggregated_output: str
    exit_code: int
    status: str


class ExecutionTransportPayload(TypedDict, total=False):
    type: object
    text: object
    item: object
    tool_name: object
    call_id: object
    arguments: object
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
