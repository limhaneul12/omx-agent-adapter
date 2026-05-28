from omx_remote.schemas.teamwork.admin_aggregation_schemas import TeamAdminAggregationReport
from omx_remote.teamwork.team_proof_layers import build_team_proof_layers


def _report(
    *,
    merge_ready: bool = False,
    completed_workers: tuple[str, ...] = (),
    missing_workers: tuple[str, ...] = (),
    blocked_workers: tuple[str, ...] = (),
    startup_issue_workers: tuple[str, ...] = (),
    incomplete_workers: tuple[str, ...] = (),
    task_count: int = 0,
    event_count: int = 0,
    requires_human_review: bool = False,
) -> TeamAdminAggregationReport:
    aggregation_state = "ready_for_ralph_review" if merge_ready else "waiting_for_workers"
    if requires_human_review:
        aggregation_state = "human_review_required"

    report = TeamAdminAggregationReport(
        admin_id="team-admin",
        aggregation_state=aggregation_state,
        merge_ready=merge_ready,
        final_report_required=True,
        completed_workers=completed_workers,
        missing_workers=missing_workers,
        blocked_workers=blocked_workers,
        startup_issue_workers=startup_issue_workers,
        incomplete_workers=incomplete_workers,
        requires_human_review=requires_human_review,
        requires_llm_review=True,
        task_count=task_count,
        event_count=event_count,
        summary="Team Admin test report.",
    )
    return report


def _states(report: TeamAdminAggregationReport) -> dict[str, str]:
    layers = build_team_proof_layers(report)
    states = {layer.name: layer.state for layer in layers}
    return states


def test_team_proof_layers_mark_all_missing_without_assignment_evidence() -> None:
    states = _states(_report())

    assert states == {
        "prd_dag_import": "missing",
        "assignment": "missing",
        "worker_readiness": "missing",
        "dispatch": "missing",
        "completion": "missing",
    }


def test_team_proof_layers_mark_assignment_only_as_waiting_for_runtime_evidence() -> None:
    states = _states(
        _report(
            missing_workers=("worker-1", "worker-2"),
            incomplete_workers=("worker-1", "worker-2"),
        )
    )

    assert states["prd_dag_import"] == "passed"
    assert states["assignment"] == "passed"
    assert states["worker_readiness"] == "partial"
    assert states["dispatch"] == "missing"
    assert states["completion"] == "missing"


def test_team_proof_layers_keep_startup_timeout_in_worker_readiness_layer() -> None:
    layers = build_team_proof_layers(
        _report(
            completed_workers=("worker-1", "worker-2"),
            startup_issue_workers=("worker-3",),
            incomplete_workers=("worker-3",),
            task_count=2,
            event_count=3,
        )
    )
    by_name = {layer.name: layer for layer in layers}

    assert by_name["worker_readiness"].state == "failed"
    assert by_name["worker_readiness"].blocking is True
    assert "worker-3" in by_name["worker_readiness"].summary
    assert by_name["completion"].state == "partial"


def test_team_proof_layers_mark_partial_completion_without_merge_claim() -> None:
    states = _states(
        _report(
            completed_workers=("worker-1",),
            missing_workers=("worker-2",),
            incomplete_workers=("worker-2",),
            task_count=1,
            event_count=1,
            requires_human_review=True,
        )
    )

    assert states["dispatch"] == "partial"
    assert states["completion"] == "failed"


def test_team_proof_layers_mark_merge_ready_when_all_completion_evidence_passes() -> None:
    layers = build_team_proof_layers(
        _report(
            merge_ready=True,
            completed_workers=("worker-1", "worker-2", "worker-3"),
            task_count=3,
            event_count=3,
        )
    )
    by_name = {layer.name: layer for layer in layers}

    assert {layer.state for layer in layers} == {"passed"}
    assert all(layer.blocking is False for layer in layers)
    assert by_name["completion"].summary == "All 3 assigned workers completed; merge-ready evidence is present."
