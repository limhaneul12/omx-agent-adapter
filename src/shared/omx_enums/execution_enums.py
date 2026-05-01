from enum import StrEnum


class ExecutionEventKind(StrEnum):
    THREAD_STARTED = "thread.started"
    TURN_STARTED = "turn.started"
    ITEM_COMPLETED = "item.completed"
    TURN_COMPLETED = "turn.completed"
