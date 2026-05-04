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
