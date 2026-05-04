from omx_remote.adapter_types.execution_types import (
    ExecMessageNormalizedPayload,
    ExecOutputNormalizedPayload,
    ExecToolCallNormalizedPayload,
    ExecToolResultNormalizedPayload,
    ExecutionItemTransportPayload,
    ExecutionTransportPayload,
    ExecutionUsageTransportPayload,
)
from omx_remote.schemas.execution_schemas import (
    ExecMessage,
    ExecOutput,
    ExecToolCall,
    ExecToolResult,
    ExecutionAnomalyCategory,
    ToolInteraction,
    ToolInteractionAnomaly,
    ToolInteractionReport,
    ToolInteractionState,
)
from omx_remote.shared.exceptions.execution_exceptions import (
    UnsupportedExecutionPayloadError,
)

# Raw transport payload stays dynamic here until routing/promotion selects a stable contract.
ExecutionPayload = ExecutionTransportPayload
ExecutionContract = ExecMessage | ExecOutput | ExecToolCall | ExecToolResult
RoutedExecutionPayload = ExecutionContract | ExecutionPayload
PROMOTABLE_EXECUTION_PAYLOAD_TYPES: frozenset[str] = frozenset(
    {"message", "output_text", "tool_call", "tool_result"}
)

ANOMALY_SUMMARIES: dict[ExecutionAnomalyCategory, str] = {
    "duplicate_result": "additional tool result observed after first matched result",
    "unmatched_result": "tool result did not match any known tool call",
    "missing_result": "tool call completed without a matching tool result",
}


def _normalize_execution_item_payload(item_payload: object) -> ExecutionItemTransportPayload:
    """Normalizes one raw execution item payload into the observed stable subset."""
    if not isinstance(item_payload, dict):
        raise UnsupportedExecutionPayloadError(
            "execution item payload must be a JSON object payload"
        )

    normalized_payload: ExecutionItemTransportPayload = {}

    id_value: object | None = item_payload.get("id")
    if isinstance(id_value, str):
        normalized_payload["id"] = id_value

    type_value: object | None = item_payload.get("type")
    if isinstance(type_value, str):
        normalized_payload["type"] = type_value

    text_value: object | None = item_payload.get("text")
    if isinstance(text_value, str):
        normalized_payload["text"] = text_value

    tool_name_value: object | None = item_payload.get("tool_name")
    if isinstance(tool_name_value, str):
        normalized_payload["tool_name"] = tool_name_value

    call_id_value: object | None = item_payload.get("call_id")
    if isinstance(call_id_value, str):
        normalized_payload["call_id"] = call_id_value

    arguments_value: object | None = item_payload.get("arguments")
    if isinstance(arguments_value, str):
        normalized_payload["arguments"] = arguments_value

    command_value: object | None = item_payload.get("command")
    if isinstance(command_value, str):
        normalized_payload["command"] = command_value

    aggregated_output_value: object | None = item_payload.get("aggregated_output")
    if isinstance(aggregated_output_value, str):
        normalized_payload["aggregated_output"] = aggregated_output_value

    exit_code_value: object | None = item_payload.get("exit_code")
    if isinstance(exit_code_value, int):
        normalized_payload["exit_code"] = exit_code_value

    status_value: object | None = item_payload.get("status")
    if isinstance(status_value, str):
        normalized_payload["status"] = status_value

    return normalized_payload


def load_execution_payload(
    payload_name: str,
    payload: object,
) -> ExecutionPayload:
    """Loads one execution payload from a raw object boundary."""
    if not isinstance(payload, dict):
        raise UnsupportedExecutionPayloadError(
            f"{payload_name} must be a JSON object payload"
        )

    item_value: object | None = payload.get("item")
    normalized_item_value: ExecutionItemTransportPayload | object | None
    if isinstance(item_value, dict):
        normalized_item_value = _normalize_execution_item_payload(item_value)
    else:
        normalized_item_value = item_value

    result: ExecutionPayload = {
        "type": payload.get("type"),
        "text": payload.get("text"),
        "item": normalized_item_value,
        "tool_name": payload.get("tool_name"),
        "call_id": payload.get("call_id"),
        "arguments": payload.get("arguments"),
        "id": payload.get("id"),
        "extra": payload.get("extra"),
    }

    thread_id_value: object | None = payload.get("thread_id")
    if isinstance(thread_id_value, str):
        result["thread_id"] = thread_id_value

    usage_value: object | None = payload.get("usage")
    if isinstance(usage_value, dict):
        usage_payload: ExecutionUsageTransportPayload = {}

        input_tokens_value: object | None = usage_value.get("input_tokens")
        if isinstance(input_tokens_value, int):
            usage_payload["input_tokens"] = input_tokens_value

        cached_input_tokens_value: object | None = usage_value.get(
            "cached_input_tokens"
        )
        if isinstance(cached_input_tokens_value, int):
            usage_payload["cached_input_tokens"] = cached_input_tokens_value

        output_tokens_value: object | None = usage_value.get("output_tokens")
        if isinstance(output_tokens_value, int):
            usage_payload["output_tokens"] = output_tokens_value

        reasoning_output_tokens_value: object | None = usage_value.get(
            "reasoning_output_tokens"
        )
        if isinstance(reasoning_output_tokens_value, int):
            usage_payload["reasoning_output_tokens"] = reasoning_output_tokens_value

        result["usage"] = usage_payload
    return result


def split_event_payloads(payload: ExecutionPayload) -> list[ExecutionPayload]:
    """Splits wrapped execution events into promotable payloads.

    Args:
        payload [ExecutionPayload]: Raw execution event payload inspected for an item-completed body before contract promotion.

    Returns:
        list[ExecutionPayload]: Payload list that downstream promotion can inspect one item at a time.
    """
    event_type: object | None = payload.get("type")

    if event_type == "item.completed":
        item: object | None = payload.get("item")
        if isinstance(item, dict):
            item_payload: ExecutionPayload = load_execution_payload(
                "item.completed item payload",
                item,
            )
            if is_promotable_execution_payload(item_payload):
                split_payloads: list[ExecutionPayload] = [item_payload]
                return split_payloads

    split_payloads: list[ExecutionPayload] = [payload]
    return split_payloads


def is_promotable_execution_payload(payload: ExecutionPayload) -> bool:
    """Checks whether one raw execution payload can become a stable contract.

    Args:
        payload [ExecutionPayload]: Raw execution payload inspected before contract promotion.

    Returns:
        bool: `True` when the payload type matches a supported execution contract, otherwise `False`.
    """
    payload_type: object | None = payload.get("type")
    is_promotable: bool = isinstance(payload_type, str) and (
        payload_type in PROMOTABLE_EXECUTION_PAYLOAD_TYPES
    )
    return is_promotable


def route_execution_payload(payload: ExecutionPayload) -> RoutedExecutionPayload:
    """Routes one raw execution payload to promotion or raw passthrough.

    Args:
        payload [ExecutionPayload]: Raw execution payload after transport parsing and event splitting.

    Returns:
        RoutedExecutionPayload: Promoted execution contract for supported payload types, otherwise the raw payload passthrough lane.
    """
    if not is_promotable_execution_payload(payload):
        passthrough_payload: ExecutionPayload = payload
        return passthrough_payload

    contract: ExecutionContract = promote_execution_contract(payload)
    return contract


def promote_exec_message(payload: ExecutionPayload) -> ExecMessage:
    """Promotes a raw message payload into a stable execution contract.

    Args:
        payload [ExecutionPayload]: Raw execution payload whose fields should become an execution message contract.

    Returns:
        ExecMessage: Stable execution message contract built from the normalized raw payload.
    """
    normalized_payload: ExecMessageNormalizedPayload = {
        "kind": payload["type"],
        "text": payload["text"],
    }
    result: ExecMessage = ExecMessage.model_validate(normalized_payload)
    return result


def promote_exec_output(payload: ExecutionPayload) -> ExecOutput:
    """Promotes a raw output payload into a stable execution contract.

    Args:
        payload [ExecutionPayload]: Raw execution payload whose fields should become an execution output contract.

    Returns:
        ExecOutput: Stable execution output contract built from the normalized raw payload.
    """
    normalized_payload: ExecOutputNormalizedPayload = {
        "kind": payload["type"],
        "text": payload["text"],
    }
    result: ExecOutput = ExecOutput.model_validate(normalized_payload)
    return result


def promote_exec_tool_call(payload: ExecutionPayload) -> ExecToolCall:
    """Promotes a raw tool-call payload into a stable execution contract.

    Args:
        payload [ExecutionPayload]: Raw execution payload whose fields should become a tool-call contract.

    Returns:
        ExecToolCall: Stable execution tool-call contract built from the normalized raw payload.
    """
    normalized_payload: ExecToolCallNormalizedPayload = {
        "kind": payload["type"],
        "tool_name": payload["tool_name"],
        "call_id": payload["call_id"],
        "arguments": payload["arguments"],
    }
    result: ExecToolCall = ExecToolCall.model_validate(normalized_payload)
    return result


def promote_exec_tool_result(payload: ExecutionPayload) -> ExecToolResult:
    """Promotes a raw tool-result payload into a stable execution contract.

    Args:
        payload [ExecutionPayload]: Raw execution payload whose fields should become a tool-result contract.

    Returns:
        ExecToolResult: Stable execution tool-result contract built from the normalized raw payload.
    """
    normalized_payload: ExecToolResultNormalizedPayload = {
        "kind": payload["type"],
        "tool_name": payload["tool_name"],
        "call_id": payload["call_id"],
        "text": payload["text"],
    }
    result: ExecToolResult = ExecToolResult.model_validate(normalized_payload)
    return result


def build_tool_interaction(events: list[ExecutionContract]) -> ToolInteraction:
    """Builds one tool interaction from promoted execution events.

    Args:
        events [list[ExecutionContract]]: Promoted execution contracts scanned to find the first tool call and its first matching result.

    Returns:
        ToolInteraction: Tool interaction built from the first tool call and the first matching tool result.
    """
    tool_call: ExecToolCall = next(
        event for event in events if isinstance(event, ExecToolCall)
    )
    tool_result: ExecToolResult | None = next(
        (
            event
            for event in events
            if isinstance(event, ExecToolResult) and event.call_id == tool_call.call_id
        ),
        None,
    )
    interaction_state: ToolInteractionState
    if tool_result is None:
        interaction_state = "missing_result"
    else:
        interaction_state = "completed"
    interaction: ToolInteraction = ToolInteraction(
        state=interaction_state,
        call=tool_call,
        result=tool_result,
    )
    return interaction


def build_tool_interactions(
    events: list[ExecutionContract],
) -> list[ToolInteraction]:
    """Builds tool interactions for a full execution stream.

    Args:
        events [list[ExecutionContract]]: Promoted execution contracts collected from one execution stream.

    Returns:
        list[ToolInteraction]: Tool interactions grouped in the same order as their tool-call events.
    """
    tool_calls: list[ExecToolCall] = [
        event for event in events if isinstance(event, ExecToolCall)
    ]
    interactions: list[ToolInteraction] = [
        build_tool_interaction([tool_call, *events]) for tool_call in tool_calls
    ]
    return interactions


def _collect_tool_results_by_call_id(
    events: list[ExecutionContract],
) -> dict[str, list[ExecToolResult]]:
    """Collects tool-result contracts grouped by call identifier.

    Args:
        events [list[ExecutionContract]]: Promoted execution contracts collected from one execution stream.

    Returns:
        dict[str, list[ExecToolResult]]: Tool-result contracts grouped in stream order by their stable call identifier.
    """
    grouped_results: dict[str, list[ExecToolResult]] = {}
    event: ExecutionContract
    for event in events:
        if not isinstance(event, ExecToolResult):
            continue
        tool_results: list[ExecToolResult] = grouped_results.setdefault(
            event.call_id, []
        )
        tool_results.append(event)
    return grouped_results


def build_tool_interaction_report(
    events: list[ExecutionContract],
) -> ToolInteractionReport:
    """Builds a tool interaction report from one execution stream.

    Args:
        events [list[ExecutionContract]]: Promoted execution contracts collected from one execution stream.

    Returns:
        ToolInteractionReport: Report containing matched interactions plus duplicate, unmatched, and missing-result anomaly buckets.
    """
    interactions: list[ToolInteraction] = build_tool_interactions(events)
    matched_call_ids: set[str] = {
        interaction.call.call_id for interaction in interactions
    }
    tool_results_by_call_id: dict[str, list[ExecToolResult]] = (
        _collect_tool_results_by_call_id(events)
    )
    duplicate_results: list[ExecToolResult] = []
    call_id: str
    tool_results: list[ExecToolResult]
    for call_id, tool_results in tool_results_by_call_id.items():
        if call_id not in matched_call_ids:
            continue
        duplicate_results.extend(tool_results[1:])
    unmatched_results: list[ExecToolResult] = [
        event
        for event in events
        if isinstance(event, ExecToolResult) and event.call_id not in matched_call_ids
    ]
    missing_result_calls: list[ExecToolCall] = [
        interaction.call
        for interaction in interactions
        if interaction.state == "missing_result"
    ]
    duplicate_anomalies: list[ToolInteractionAnomaly] = [
        ToolInteractionAnomaly(
            category="duplicate_result",
            related_call_id=duplicate_result.call_id,
            tool_name=duplicate_result.tool_name,
            summary=ANOMALY_SUMMARIES["duplicate_result"],
        )
        for duplicate_result in duplicate_results
    ]
    unmatched_anomalies: list[ToolInteractionAnomaly] = [
        ToolInteractionAnomaly(
            category="unmatched_result",
            related_call_id=unmatched_result.call_id,
            tool_name=unmatched_result.tool_name,
            summary=ANOMALY_SUMMARIES["unmatched_result"],
        )
        for unmatched_result in unmatched_results
    ]
    missing_result_anomalies: list[ToolInteractionAnomaly] = [
        ToolInteractionAnomaly(
            category="missing_result",
            related_call_id=missing_result_call.call_id,
            tool_name=missing_result_call.tool_name,
            summary=ANOMALY_SUMMARIES["missing_result"],
        )
        for missing_result_call in missing_result_calls
    ]
    anomalies: list[ToolInteractionAnomaly] = [
        *duplicate_anomalies,
        *unmatched_anomalies,
        *missing_result_anomalies,
    ]
    result: ToolInteractionReport = ToolInteractionReport(
        interactions=interactions,
        duplicate_results=duplicate_results,
        unmatched_results=unmatched_results,
        missing_result_calls=missing_result_calls,
        anomalies=anomalies,
        interaction_count=len(interactions),
        completed_count=len(
            [interaction for interaction in interactions if interaction.state == "completed"]
        ),
        missing_result_count=len(missing_result_calls),
        duplicate_result_count=len(duplicate_results),
        unmatched_result_count=len(unmatched_results),
        has_anomalies=bool(anomalies),
        anomaly_count=len(anomalies),
    )
    return result


def promote_execution_contract(payload: ExecutionPayload) -> ExecutionContract:
    """Promotes one raw execution payload into a stable execution contract.

    Args:
        payload [ExecutionPayload]: Raw execution payload whose type decides the contract promotion lane.

    Returns:
        ExecutionContract: Stable execution contract built from the raw payload.

    Raises:
        UnsupportedExecutionPayloadError: Raised when the payload type is unsupported.
    """
    payload_type: object | None = payload.get("type")
    if payload_type == "message":
        result: ExecutionContract = promote_exec_message(payload)
        return result
    if payload_type == "output_text":
        result = promote_exec_output(payload)
        return result
    if payload_type == "tool_call":
        result = promote_exec_tool_call(payload)
        return result
    if payload_type == "tool_result":
        result = promote_exec_tool_result(payload)
        return result

    raise UnsupportedExecutionPayloadError(
        f"unsupported execution payload type: {payload_type}"
    )
