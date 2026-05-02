from schemas.execution_schemas import (
    ExecMessage,
    ExecOutput,
    ExecToolCall,
    ExecToolResult,
    ToolInteraction,
    ToolInteractionAnomaly,
    ToolInteractionReport,
)
from shared.exceptions.execution_exceptions import UnsupportedExecutionPayloadError

ExecutionContract = ExecMessage | ExecOutput | ExecToolCall | ExecToolResult

# Raw transport payload stays dynamic here until routing/promotion selects a stable contract.
ExecutionPayload = dict[str, object]
ToolResultKey = tuple[str, str]


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
            split_payloads: list[ExecutionPayload] = [item]
            return split_payloads

    split_payloads: list[ExecutionPayload] = [payload]
    return split_payloads


def promote_exec_message(payload: ExecutionPayload) -> ExecMessage:
    """Promotes a raw message payload into a stable execution contract.

    Args:
        payload [ExecutionPayload]: Raw execution payload whose fields should become an execution message contract.

    Returns:
        ExecMessage: Stable execution message contract built from the normalized raw payload.
    """
    normalized_payload: ExecutionPayload = {
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
    normalized_payload: ExecutionPayload = {
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
    normalized_payload: ExecutionPayload = {
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
    normalized_payload: ExecutionPayload = {
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
            if isinstance(event, ExecToolResult)
            and event.call_id == tool_call.call_id
        ),
        None,
    )
    interaction: ToolInteraction = ToolInteraction(
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
    matched_result_keys: set[ToolResultKey] = {
        (interaction.result.call_id, interaction.result.text)
        for interaction in interactions
        if interaction.result is not None
    }
    matched_call_ids: set[str] = {
        interaction.call.call_id for interaction in interactions
    }
    duplicate_results: list[ExecToolResult] = [
        event
        for event in events
        if isinstance(event, ExecToolResult)
        and event.call_id in matched_call_ids
        and (event.call_id, event.text) not in matched_result_keys
    ]
    unmatched_results: list[ExecToolResult] = [
        event
        for event in events
        if isinstance(event, ExecToolResult)
        and event.call_id not in matched_call_ids
    ]
    missing_result_calls: list[ExecToolCall] = [
        interaction.call
        for interaction in interactions
        if interaction.result is None
    ]
    anomalies: list[ToolInteractionAnomaly] = [
        *[
            ToolInteractionAnomaly(
                category="duplicate_result",
                related_call_id=result.call_id,
                tool_name=result.tool_name,
            )
            for result in duplicate_results
        ],
        *[
            ToolInteractionAnomaly(
                category="unmatched_result",
                related_call_id=result.call_id,
                tool_name=result.tool_name,
            )
            for result in unmatched_results
        ],
        *[
            ToolInteractionAnomaly(
                category="missing_result",
                related_call_id=call.call_id,
                tool_name=call.tool_name,
            )
            for call in missing_result_calls
        ],
    ]
    report: ToolInteractionReport = ToolInteractionReport(
        interactions=interactions,
        unmatched_results=unmatched_results,
        duplicate_results=duplicate_results,
        missing_result_calls=missing_result_calls,
        anomalies=anomalies,
    )
    return report


def promote_execution_contract(payload: ExecutionPayload) -> ExecutionContract:
    """Promotes one raw execution payload into the matching stable contract.

    Args:
        payload [ExecutionPayload]: Raw execution payload after transport parsing and event splitting.

    Returns:
        ExecutionContract: Stable execution contract selected from the payload type.
    """
    payload_type: object | None = payload.get("type")

    if payload_type == "message":
        contract: ExecutionContract = promote_exec_message(payload)
        return contract
    if payload_type == "output_text":
        contract = promote_exec_output(payload)
        return contract
    if payload_type == "tool_call":
        contract = promote_exec_tool_call(payload)
        return contract
    if payload_type == "tool_result":
        contract = promote_exec_tool_result(payload)
        return contract

    raise UnsupportedExecutionPayloadError(
        f"unsupported execution payload type: {payload_type}"
    )
