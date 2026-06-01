from omx_remote.adapter_types.execution_types import (
    KnownExecutionEventTypeSet,
    PromotableExecutionPayloadTypeSet,
)
from omx_remote.shared.omx_enums.execution_enums import (
    ExecutionAnomalyCategory,
    KnownExecutionEventType,
    PromotableExecutionPayloadType,
)

PROMOTABLE_EXECUTION_PAYLOAD_TYPES: PromotableExecutionPayloadTypeSet = frozenset(
    PromotableExecutionPayloadType
)
KNOWN_EXECUTION_EVENT_TYPES: KnownExecutionEventTypeSet = frozenset(
    KnownExecutionEventType
)

ANOMALY_SUMMARIES: dict[ExecutionAnomalyCategory, str] = {
    ExecutionAnomalyCategory.DUPLICATE_RESULT: "additional tool result observed after first matched result",
    ExecutionAnomalyCategory.UNMATCHED_RESULT: "tool result did not match any known tool call",
    ExecutionAnomalyCategory.MISSING_RESULT: "tool call completed without a matching tool result",
}
