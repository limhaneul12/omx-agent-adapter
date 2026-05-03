from typing import Required, TypedDict


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
