from enum import StrEnum


class ExecutionEventKind(StrEnum):
    THREAD_STARTED = "thread.started"
    TURN_STARTED = "turn.started"
    ITEM_COMPLETED = "item.completed"
    TURN_COMPLETED = "turn.completed"


class ExecutionPayloadKind(StrEnum):
    MESSAGE = "message"
    OUTPUT_TEXT = "output_text"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    COMMAND_EXECUTION = "command_execution"


class ToolInteractionState(StrEnum):
    COMPLETED = "completed"
    MISSING_RESULT = "missing_result"


class ExecutionAnomalyCategory(StrEnum):
    UNMATCHED_RESULT = "unmatched_result"
    DUPLICATE_RESULT = "duplicate_result"
    MISSING_RESULT = "missing_result"
