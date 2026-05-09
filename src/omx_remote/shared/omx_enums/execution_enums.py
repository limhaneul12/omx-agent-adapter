from enum import StrEnum


class ExecutionEventKind(StrEnum):
    """Execution event kind values normalized from the transport stream."""

    THREAD_STARTED = "thread.started"
    TURN_STARTED = "turn.started"
    ITEM_COMPLETED = "item.completed"
    TURN_COMPLETED = "turn.completed"


class ExecutionItemStableFieldKey(StrEnum):
    """Stable execution item field keys promoted by the adapter."""

    ID = "id"
    TYPE = "type"
    TEXT = "text"
    TOOL_NAME = "tool_name"
    CALL_ID = "call_id"
    ARGUMENTS = "arguments"
    COMMAND = "command"
    AGGREGATED_OUTPUT = "aggregated_output"
    EXIT_CODE = "exit_code"
    STATUS = "status"


class ExecutionTransportStableFieldKey(StrEnum):
    """Stable top-level execution transport field keys promoted by the adapter."""

    TYPE = "type"
    TEXT = "text"
    ITEM = "item"
    TOOL_NAME = "tool_name"
    CALL_ID = "call_id"
    ARGUMENTS = "arguments"
    COMMAND = "command"
    AGGREGATED_OUTPUT = "aggregated_output"
    EXIT_CODE = "exit_code"
    STATUS = "status"
    ID = "id"
    EXTRA = "extra"
    KIND = "kind"
    THREAD_ID = "thread_id"
    USAGE = "usage"


class KnownExecutionEventType(StrEnum):
    """Execution event types recognized by the adapter execution stream layer."""

    THREAD_STARTED = "thread.started"
    TURN_STARTED = "turn.started"
    ITEM_COMPLETED = "item.completed"
    TURN_COMPLETED = "turn.completed"


class ExecutionPayloadKind(StrEnum):
    """Execution payload contract kinds emitted by adapter-owned promotion."""

    MESSAGE = "message"
    OUTPUT_TEXT = "output_text"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    COMMAND_EXECUTION = "command_execution"


class PromotableExecutionPayloadType(StrEnum):
    """Execution payload item types promotable into stable adapter contracts."""

    MESSAGE = "message"
    OUTPUT_TEXT = "output_text"
    COMMAND_EXECUTION = "command_execution"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"


class ToolInteractionState(StrEnum):
    """Tool interaction states derived from execution tool-call/result matching."""

    COMPLETED = "completed"
    MISSING_RESULT = "missing_result"


class ExecutionAnomalyCategory(StrEnum):
    """Execution anomaly categories reported by tool interaction analysis."""

    UNMATCHED_RESULT = "unmatched_result"
    DUPLICATE_RESULT = "duplicate_result"
    MISSING_RESULT = "missing_result"
