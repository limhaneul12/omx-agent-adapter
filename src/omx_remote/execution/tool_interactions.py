from omx_remote.adapter_types.execution_types import ExecutionContract
from omx_remote.adapter_types.type_contract.execution_contract_type import (
    ANOMALY_SUMMARIES,
)
from omx_remote.schemas.execution.event_schemas import (
    ExecToolCall,
    ExecToolResult,
)
from omx_remote.schemas.execution.interaction_schemas import (
    ToolInteraction,
    ToolInteractionAnomaly,
    ToolInteractionReport,
)
from omx_remote.shared.omx_enums.execution_enums import (
    ExecutionAnomalyCategory,
    ToolInteractionState,
)


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
        interaction_state = ToolInteractionState.MISSING_RESULT
    else:
        interaction_state = ToolInteractionState.COMPLETED
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
        if interaction.state == ToolInteractionState.MISSING_RESULT
    ]
    duplicate_anomalies: list[ToolInteractionAnomaly] = [
        ToolInteractionAnomaly(
            category=ExecutionAnomalyCategory.DUPLICATE_RESULT,
            related_call_id=duplicate_result.call_id,
            tool_name=duplicate_result.tool_name,
            summary=ANOMALY_SUMMARIES[ExecutionAnomalyCategory.DUPLICATE_RESULT],
        )
        for duplicate_result in duplicate_results
    ]
    unmatched_anomalies: list[ToolInteractionAnomaly] = [
        ToolInteractionAnomaly(
            category=ExecutionAnomalyCategory.UNMATCHED_RESULT,
            related_call_id=unmatched_result.call_id,
            tool_name=unmatched_result.tool_name,
            summary=ANOMALY_SUMMARIES[ExecutionAnomalyCategory.UNMATCHED_RESULT],
        )
        for unmatched_result in unmatched_results
    ]
    missing_result_anomalies: list[ToolInteractionAnomaly] = [
        ToolInteractionAnomaly(
            category=ExecutionAnomalyCategory.MISSING_RESULT,
            related_call_id=missing_result_call.call_id,
            tool_name=missing_result_call.tool_name,
            summary=ANOMALY_SUMMARIES[ExecutionAnomalyCategory.MISSING_RESULT],
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
            [
                interaction
                for interaction in interactions
                if interaction.state == ToolInteractionState.COMPLETED
            ]
        ),
        missing_result_count=len(missing_result_calls),
        duplicate_result_count=len(duplicate_results),
        unmatched_result_count=len(unmatched_results),
        has_anomalies=bool(anomalies),
        anomaly_count=len(anomalies),
    )
    return result
