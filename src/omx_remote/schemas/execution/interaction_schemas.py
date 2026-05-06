from __future__ import annotations

from pydantic import model_validator

from omx_remote.schemas.common_schemas import (
    NonEmptyString,
    StrictSchemaModel,
)
from omx_remote.schemas.execution.event_schemas import ExecToolCall, ExecToolResult
from omx_remote.shared.omx_enums.execution_enums import (
    ExecutionAnomalyCategory,
    ToolInteractionState,
)


class ToolInteractionAnomaly(StrictSchemaModel):
    """Represents a normalized anomaly from tool interaction grouping."""

    category: ExecutionAnomalyCategory
    related_call_id: NonEmptyString
    tool_name: NonEmptyString
    summary: NonEmptyString


class ToolInteraction(StrictSchemaModel):
    """Represents one tool call paired with its first matching result."""

    state: ToolInteractionState
    call: ExecToolCall
    result: ExecToolResult | None = None

    @model_validator(mode="after")
    def _validate_state(self) -> ToolInteraction:
        """Validates that the state of the interaction matches whether a result is present.
        
        Returns:
            ToolInteraction: Function return value.
        """
        expected_state: ToolInteractionState
        if self.result is None:
            expected_state = ToolInteractionState.MISSING_RESULT
        else:
            expected_state = ToolInteractionState.COMPLETED
        if self.state != expected_state:
            raise ValueError(
                "ToolInteraction.state must match whether result is present"
            )
        if self.result is not None and self.result.call_id != self.call.call_id:
            raise ValueError(
                "ToolInteraction.result.call_id must match ToolInteraction.call.call_id"
            )
        if self.result is not None and self.result.tool_name != self.call.tool_name:
            raise ValueError(
                "ToolInteraction.result.tool_name must match ToolInteraction.call.tool_name"
            )
        validated_interaction: ToolInteraction = self
        return validated_interaction


class ToolInteractionReport(StrictSchemaModel):
    """Represents grouped tool interactions plus anomaly buckets."""

    interactions: tuple[ToolInteraction, ...]
    unmatched_results: tuple[ExecToolResult, ...]
    duplicate_results: tuple[ExecToolResult, ...]
    missing_result_calls: tuple[ExecToolCall, ...]
    anomalies: tuple[ToolInteractionAnomaly, ...]
    interaction_count: int
    completed_count: int
    missing_result_count: int
    duplicate_result_count: int
    unmatched_result_count: int
    has_anomalies: bool
    anomaly_count: int

    @model_validator(mode="after")
    def _validate_summary_counts(self) -> ToolInteractionReport:
        """Validates that derived summary counters match the underlying lists.
        
        Returns:
            ToolInteractionReport: Function return value.
        """
        expected_interaction_count: int = len(self.interactions)

        if self.interaction_count != expected_interaction_count:
            raise ValueError(
                "ToolInteractionReport.interaction_count must match interactions"
            )

        expected_completed_count: int = len(
            [
                interaction
                for interaction in self.interactions
                if interaction.state == ToolInteractionState.COMPLETED
            ]
        )
        if self.completed_count != expected_completed_count:
            raise ValueError(
                "ToolInteractionReport.completed_count must match completed interactions"
            )

        expected_missing_result_count = len(self.missing_result_calls)
        if self.missing_result_count != expected_missing_result_count:
            raise ValueError(
                "ToolInteractionReport.missing_result_count must match missing_result_calls"
            )

        expected_duplicate_result_count = len(self.duplicate_results)
        if self.duplicate_result_count != expected_duplicate_result_count:
            raise ValueError(
                "ToolInteractionReport.duplicate_result_count must match duplicate_results"
            )

        expected_unmatched_result_count = len(self.unmatched_results)
        if self.unmatched_result_count != expected_unmatched_result_count:
            raise ValueError(
                "ToolInteractionReport.unmatched_result_count must match unmatched_results"
            )

        expected_anomaly_count: int = (
            expected_duplicate_result_count
            + expected_unmatched_result_count
            + expected_missing_result_count
        )
        if len(self.anomalies) != expected_anomaly_count:
            raise ValueError(
                "ToolInteractionReport.anomalies must include one entry per derived anomaly"
            )
        if self.anomaly_count != expected_anomaly_count:
            raise ValueError(
                "ToolInteractionReport.anomaly_count must match anomalies"
            )
        expected_has_anomalies = expected_anomaly_count > 0
        if self.has_anomalies != expected_has_anomalies:
            raise ValueError(
                "ToolInteractionReport.has_anomalies must match anomaly_count"
            )

        validated_report: ToolInteractionReport = self
        return validated_report
