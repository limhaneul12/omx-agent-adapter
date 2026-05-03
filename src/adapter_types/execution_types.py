from typing import TypedDict


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
    kind: object
    text: object


class ExecOutputNormalizedPayload(TypedDict):
    kind: object
    text: object


class ExecToolCallNormalizedPayload(TypedDict):
    kind: object
    tool_name: object
    call_id: object
    arguments: object


class ExecToolResultNormalizedPayload(TypedDict):
    kind: object
    tool_name: object
    call_id: object
    text: object
