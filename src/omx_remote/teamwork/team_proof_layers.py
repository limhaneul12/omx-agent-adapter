from omx_remote.schemas.teamwork.admin_aggregation_schemas import (
    TeamAdminAggregationReport,
)
from omx_remote.schemas.teamwork.proof_layer_schemas import (
    TeamProofLayerName,
    TeamProofLayerState,
    TeamProofLayerSummary,
)


def normalize_proof_state_token(state_text: str) -> str:
    """Normalize external state text for proof-layer classification.

    Args:
        state_text [str]: External state text.

    Returns:
        str: Lowercase underscore-delimited state token.
    """
    normalized_state: str = state_text.strip().lower().replace("-", "_")
    return normalized_state


def build_team_proof_layers(
    report: TeamAdminAggregationReport,
) -> tuple[TeamProofLayerSummary, ...]:
    """Build proof-layer summaries from a Team Admin aggregation report.

    Args:
        report [TeamAdminAggregationReport]: Aggregated Team Admin evidence.

    Returns:
        tuple[TeamProofLayerSummary, ...]: Ordered evidence layers.
    """
    assigned_worker_count: int = _count_report_workers(report)
    layers: tuple[TeamProofLayerSummary, ...] = (
        _build_prd_dag_import_layer(report, assigned_worker_count),
        _build_assignment_layer(assigned_worker_count),
        _build_worker_readiness_layer(report, assigned_worker_count),
        _build_dispatch_layer(report, assigned_worker_count),
        _build_completion_layer(report, assigned_worker_count),
    )
    return layers


def _count_report_workers(report: TeamAdminAggregationReport) -> int:
    """Count unique workers represented in an aggregation report.

    Args:
        report [TeamAdminAggregationReport]: Team Admin aggregation report.

    Returns:
        int: Number of unique worker IDs represented by the report.
    """
    worker_ids: set[str] = set()
    worker_ids.update(report.completed_workers)
    worker_ids.update(report.missing_workers)
    worker_ids.update(report.blocked_workers)
    worker_ids.update(report.startup_issue_workers)
    worker_ids.update(report.incomplete_workers)
    worker_count: int = len(worker_ids)
    return worker_count


def _build_prd_dag_import_layer(
    report: TeamAdminAggregationReport,
    assigned_worker_count: int,
) -> TeamProofLayerSummary:
    """Build the Ralph PRD/DAG/import proof layer.

    Args:
        report [TeamAdminAggregationReport]: Team Admin aggregation report.
        assigned_worker_count [int]: Unique worker count represented in the report.

    Returns:
        TeamProofLayerSummary: PRD/DAG/import proof-layer summary.
    """
    state: TeamProofLayerState = TeamProofLayerState.PASSED
    summary: str = (
        f"Ralph PRD/Team Admin import evidence is present for admin {report.admin_id}."
    )
    blocking: bool = False
    if assigned_worker_count == 0:
        state = TeamProofLayerState.MISSING
        summary = "No Ralph PRD/DAG/import worker evidence is present."
        blocking = True

    layer = TeamProofLayerSummary(
        name=TeamProofLayerName.PRD_DAG_IMPORT,
        state=state,
        summary=summary,
        source_names=("ralph_prd_artifact", "team_admin_policy"),
        blocking=blocking,
    )
    return layer


def _build_assignment_layer(assigned_worker_count: int) -> TeamProofLayerSummary:
    """Build the Team worker-assignment proof layer.

    Args:
        assigned_worker_count [int]: Unique worker count represented in the report.

    Returns:
        TeamProofLayerSummary: Assignment proof-layer summary.
    """
    state: TeamProofLayerState = TeamProofLayerState.MISSING
    summary: str = "No Team worker assignment evidence is present."
    blocking: bool = True
    if assigned_worker_count:
        state = TeamProofLayerState.PASSED
        summary = f"{assigned_worker_count} Team worker assignment record is present."
        blocking = False

    layer = TeamProofLayerSummary(
        name=TeamProofLayerName.ASSIGNMENT,
        state=state,
        summary=summary,
        source_names=("ralph_prd_artifact", "team_worker_assignments"),
        blocking=blocking,
    )
    return layer


def _build_worker_readiness_layer(
    report: TeamAdminAggregationReport,
    assigned_worker_count: int,
) -> TeamProofLayerSummary:
    """Build the worker-readiness proof layer.

    Args:
        report [TeamAdminAggregationReport]: Team Admin aggregation report.
        assigned_worker_count [int]: Unique worker count represented in the report.

    Returns:
        TeamProofLayerSummary: Worker-readiness proof-layer summary.
    """
    state: TeamProofLayerState = TeamProofLayerState.PASSED
    summary: str = f"Worker readiness is sufficiently proven for {assigned_worker_count} assigned workers."
    blocking: bool = False
    source_names: tuple[str, ...] = ("omx_team_api_read_worker_status",)
    if assigned_worker_count == 0:
        state = TeamProofLayerState.MISSING
        summary = "No worker readiness evidence is present."
        blocking = True
    elif report.startup_issue_workers:
        state = TeamProofLayerState.FAILED
        startup_workers_text: str = ", ".join(report.startup_issue_workers)
        summary = f"Worker readiness failed for startup issue workers: {startup_workers_text}."
        blocking = True
        source_names = (
            "omx_team_api_read_worker_status",
            "omx_team_api_read_events",
            "omx_team_startup_timing",
        )
    elif report.incomplete_workers:
        state = TeamProofLayerState.PARTIAL
        incomplete_workers_text: str = ", ".join(report.incomplete_workers)
        summary = f"Worker readiness remains partial for incomplete workers: {incomplete_workers_text}."
        blocking = True

    layer = TeamProofLayerSummary(
        name=TeamProofLayerName.WORKER_READINESS,
        state=state,
        summary=summary,
        source_names=source_names,
        blocking=blocking,
    )
    return layer


def _build_dispatch_layer(
    report: TeamAdminAggregationReport,
    assigned_worker_count: int,
) -> TeamProofLayerSummary:
    """Build the task-dispatch proof layer.

    Args:
        report [TeamAdminAggregationReport]: Team Admin aggregation report.
        assigned_worker_count [int]: Unique worker count represented in the report.

    Returns:
        TeamProofLayerSummary: Dispatch proof-layer summary.
    """
    state: TeamProofLayerState = TeamProofLayerState.PASSED
    summary: str = (
        f"Dispatch/task evidence covers {report.task_count} task and "
        f"{report.event_count} Team event record."
    )
    blocking: bool = False
    if assigned_worker_count == 0 or (
        report.task_count == 0 and report.event_count == 0
    ):
        state = TeamProofLayerState.MISSING
        summary = "No Team dispatch, task, or hook receipt evidence is present."
        blocking = True
    elif report.task_count < assigned_worker_count or report.incomplete_workers:
        state = TeamProofLayerState.PARTIAL
        summary = (
            f"Dispatch evidence is partial: {report.task_count}/{assigned_worker_count} "
            "assigned workers have task evidence."
        )
        blocking = True

    layer = TeamProofLayerSummary(
        name=TeamProofLayerName.DISPATCH,
        state=state,
        summary=summary,
        source_names=("omx_team_api_list_tasks", "omx_team_api_read_events"),
        blocking=blocking,
    )
    return layer


def _build_completion_layer(
    report: TeamAdminAggregationReport,
    assigned_worker_count: int,
) -> TeamProofLayerSummary:
    """Build the worker-completion proof layer.

    Args:
        report [TeamAdminAggregationReport]: Team Admin aggregation report.
        assigned_worker_count [int]: Unique worker count represented in the report.

    Returns:
        TeamProofLayerSummary: Completion proof-layer summary.
    """
    state: TeamProofLayerState = TeamProofLayerState.MISSING
    summary: str = "No worker completion evidence is present."
    blocking: bool = True
    if report.merge_ready:
        state = TeamProofLayerState.PASSED
        summary = (
            f"All {assigned_worker_count} assigned workers completed; "
            "merge-ready evidence is present."
        )
        blocking = False
    elif report.blocked_workers or report.requires_human_review:
        state = TeamProofLayerState.FAILED
        summary = "Completion evidence is blocked or requires human review."
    elif report.completed_workers:
        state = TeamProofLayerState.PARTIAL
        summary = (
            f"{len(report.completed_workers)}/{assigned_worker_count} assigned workers "
            "have completed output."
        )

    layer = TeamProofLayerSummary(
        name=TeamProofLayerName.COMPLETION,
        state=state,
        summary=summary,
        source_names=("team_admin_aggregation_report", "omx_team_api_list_tasks"),
        blocking=blocking,
    )
    return layer
