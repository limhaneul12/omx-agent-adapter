import asyncio
from pathlib import Path

from omx_remote.schemas.ralph.prd_schemas import RalphPrdArtifact
from omx_remote.schemas.teamwork.admin_aggregation_schemas import (
    TeamAdminAggregationReportRequest,
)
from omx_remote.schemas.teamwork.api_snapshot_schemas import (
    TeamApiEventSnapshot,
    TeamApiListTasksSnapshot,
    TeamApiReadEventsSnapshot,
    TeamApiTaskSnapshot,
    TeamApiWorkerStatusSnapshot,
)
from omx_remote.teamwork import team_admin_aggregation
from omx_remote.teamwork.team_admin_aggregation import (
    build_team_admin_aggregation_report,
    read_team_admin_aggregation_report,
    write_team_admin_aggregation_report_artifact,
)


def _assignment(worker_id: str, owned_file: str) -> dict[str, object]:
    return {
        "worker_id": worker_id,
        "lane_name": f"{worker_id} lane",
        "objective": f"Complete {worker_id} assignment",
        "owned_files": [owned_file],
        "read_only_context_files": ["AGENTS.md"],
        "forbidden_files": [".omx/**"],
        "tdd_steps": ["write failing test", "make it pass"],
        "verification_commands": [
            "uv run pytest tests/teamwork/test_team_admin_aggregation.py -q"
        ],
        "handoff_summary_required": "report verification and changed files",
        "authorization_policy": "llm_review",
        "authorization_scope": {
            "allowed_commands": [
                "uv run pytest tests/teamwork/test_team_admin_aggregation.py -q"
            ],
            "forbidden_commands": ["git push"],
            "requires_human_for": ["change files outside owned_files"],
            "requires_llm_review_for": ["local checkpoint commit"],
        },
    }


def _team_admin() -> dict[str, object]:
    return {
        "admin_id": "team-admin",
        "aggregation_policy": "collect_all_workers_then_review",
        "merge_policy": "review_before_merge",
        "completion_policy": "all_required_tasks_completed",
        "requires_human_for": ["missing, blocked, or conflicting worker output"],
        "requires_llm_review_for": ["final aggregation report before Ralph review"],
        "final_report_required": True,
    }


def _prd_artifact() -> RalphPrdArtifact:
    return RalphPrdArtifact.model_validate(
        {
            "objective": "ship Team Admin aggregation report builder",
            "scope": ["aggregate Team worker results for Ralph review"],
            "constraints": ["Team Admin collects results; Ralph reviews the report"],
            "execution_plan": [
                "build final aggregation report from Team API snapshots"
            ],
            "verification_expectations": [
                "report blocks merge when workers are missing"
            ],
            "requires_team_fanout": True,
            "team_worker_count": 3,
            "continuation_policy": "review_required",
            "team_worker_assignments": [
                _assignment("worker-1", "src/a.py"),
                _assignment("worker-2", "src/b.py"),
                _assignment("worker-3", "src/c.py"),
            ],
            "team_admin": _team_admin(),
        }
    )


def test_team_admin_aggregation_report_marks_clean_wave_ready_for_ralph_review() -> (
    None
):
    report = build_team_admin_aggregation_report(
        ralph_prd_artifact=_prd_artifact(),
        task_snapshot=TeamApiListTasksSnapshot(
            count=3,
            tasks=(
                TeamApiTaskSnapshot(
                    id="task-1",
                    subject="worker-1 handoff",
                    status="completed",
                    owner="worker-1",
                ),
                TeamApiTaskSnapshot(
                    id="task-2",
                    subject="worker-2 handoff",
                    status="done",
                    owner="worker-2",
                ),
                TeamApiTaskSnapshot(
                    id="task-3",
                    subject="worker-3 handoff",
                    status="success",
                    owner="worker-3",
                ),
            ),
        ),
        event_snapshot=TeamApiReadEventsSnapshot(
            count=1,
            cursor="1",
            events=(
                TeamApiEventSnapshot(
                    type="handoff_submitted", worker="worker-1", task_id="task-1"
                ),
            ),
        ),
        worker_statuses=(
            TeamApiWorkerStatusSnapshot(
                worker="worker-1", state="idle", updated_at="2026-05-06T00:00:00Z"
            ),
            TeamApiWorkerStatusSnapshot(
                worker="worker-2", state="completed", updated_at="2026-05-06T00:00:00Z"
            ),
            TeamApiWorkerStatusSnapshot(
                worker="worker-3", state="success", updated_at="2026-05-06T00:00:00Z"
            ),
        ),
    )

    assert report.admin_id == "team-admin"
    assert report.aggregation_state == "ready_for_ralph_review"
    assert report.merge_ready is True
    assert report.final_report_required is True
    assert report.completed_workers == ("worker-1", "worker-2", "worker-3")
    assert report.missing_workers == ()
    assert report.blocked_workers == ()
    assert report.incomplete_workers == ()
    assert report.requires_human_review is False
    assert report.requires_llm_review is True
    assert (
        report.summary
        == "Team Admin collected 3/3 completed worker results; ready for Ralph review."
    )
    assert tuple(layer.name for layer in report.proof_layers) == (
        "prd_dag_import",
        "assignment",
        "worker_readiness",
        "dispatch",
        "completion",
    )
    assert {layer.state for layer in report.proof_layers} == {"passed"}


def test_team_admin_aggregation_report_blocks_merge_for_missing_and_blocked_workers() -> (
    None
):
    report = build_team_admin_aggregation_report(
        ralph_prd_artifact=_prd_artifact(),
        task_snapshot=TeamApiListTasksSnapshot(
            count=2,
            tasks=(
                TeamApiTaskSnapshot(
                    id="task-1",
                    subject="worker-1 handoff",
                    status="completed",
                    owner="worker-1",
                ),
                TeamApiTaskSnapshot(
                    id="task-2",
                    subject="worker-2 handoff",
                    status="blocked",
                    owner="worker-2",
                ),
            ),
        ),
        event_snapshot=TeamApiReadEventsSnapshot(
            count=2,
            cursor="2",
            events=(
                TeamApiEventSnapshot(
                    type="handoff_submitted", worker="worker-1", task_id="task-1"
                ),
                TeamApiEventSnapshot(
                    type="blocked", worker="worker-2", task_id="task-2"
                ),
            ),
        ),
        worker_statuses=(
            TeamApiWorkerStatusSnapshot(
                worker="worker-1", state="idle", updated_at="2026-05-06T00:00:00Z"
            ),
            TeamApiWorkerStatusSnapshot(
                worker="worker-2", state="blocked", updated_at="2026-05-06T00:00:00Z"
            ),
        ),
    )

    assert report.aggregation_state == "human_review_required"
    assert report.merge_ready is False
    assert report.completed_workers == ("worker-1",)
    assert report.blocked_workers == ("worker-2",)
    assert report.missing_workers == ("worker-3",)
    assert report.startup_issue_workers == ()
    assert report.incomplete_workers == ("worker-2", "worker-3")
    assert report.requires_human_review is True
    assert report.requires_llm_review is True
    assert report.task_count == 2
    assert report.event_count == 2
    assert (
        report.summary
        == "Team Admin found 1 completed, 1 blocked, and 1 missing worker result; human review required."
    )


def test_team_admin_aggregation_report_surfaces_ready_prompt_timeout_as_follow_up_not_human_review() -> (
    None
):
    report = build_team_admin_aggregation_report(
        ralph_prd_artifact=_prd_artifact(),
        task_snapshot=TeamApiListTasksSnapshot(
            count=2,
            tasks=(
                TeamApiTaskSnapshot(
                    id="task-1",
                    subject="worker-1 handoff",
                    status="completed",
                    owner="worker-1",
                ),
                TeamApiTaskSnapshot(
                    id="task-2",
                    subject="worker-2 handoff",
                    status="completed",
                    owner="worker-2",
                ),
            ),
        ),
        event_snapshot=TeamApiReadEventsSnapshot(
            count=3,
            cursor="3",
            events=(
                TeamApiEventSnapshot(
                    type="handoff_submitted", worker="worker-1", task_id="task-1"
                ),
                TeamApiEventSnapshot(
                    type="handoff_submitted", worker="worker-2", task_id="task-2"
                ),
                TeamApiEventSnapshot(type="ready_prompt_timeout", worker="worker-3"),
            ),
        ),
        worker_statuses=(
            TeamApiWorkerStatusSnapshot(
                worker="worker-1", state="idle", updated_at="2026-05-06T00:00:00Z"
            ),
            TeamApiWorkerStatusSnapshot(
                worker="worker-2", state="idle", updated_at="2026-05-06T00:00:00Z"
            ),
            TeamApiWorkerStatusSnapshot(
                worker="worker-3",
                state="unknown",
                updated_at="1970-01-01T00:00:00.000Z",
            ),
        ),
    )

    assert report.aggregation_state == "waiting_for_workers"
    assert report.merge_ready is False
    assert report.completed_workers == ("worker-1", "worker-2")
    assert report.missing_workers == ()
    assert report.startup_issue_workers == ("worker-3",)
    assert report.incomplete_workers == ("worker-3",)
    assert report.requires_human_review is False
    assert "1 startup issue" in report.summary
    worker_readiness_layer = next(
        layer for layer in report.proof_layers if layer.name == "worker_readiness"
    )
    assert worker_readiness_layer.state == "failed"
    assert worker_readiness_layer.blocking is True
    assert "worker-3" in worker_readiness_layer.summary


def test_team_admin_aggregation_report_keeps_worker_startup_timeout_in_readiness_layer() -> (
    None
):
    report = build_team_admin_aggregation_report(
        ralph_prd_artifact=_prd_artifact(),
        task_snapshot=TeamApiListTasksSnapshot(
            count=2,
            tasks=(
                TeamApiTaskSnapshot(
                    id="task-1",
                    subject="worker-1 handoff",
                    status="completed",
                    owner="worker-1",
                ),
                TeamApiTaskSnapshot(
                    id="task-2",
                    subject="worker-2 handoff",
                    status="completed",
                    owner="worker-2",
                ),
            ),
        ),
        event_snapshot=TeamApiReadEventsSnapshot(count=0, cursor="", events=()),
        worker_statuses=(
            TeamApiWorkerStatusSnapshot(
                worker="worker-1",
                state="idle",
                updated_at="2026-05-06T00:00:00Z",
            ),
            TeamApiWorkerStatusSnapshot(
                worker="worker-2",
                state="idle",
                updated_at="2026-05-06T00:00:00Z",
            ),
            TeamApiWorkerStatusSnapshot(
                worker="worker-3",
                state="worker_startup_timeout",
                updated_at="2026-05-06T00:00:00Z",
            ),
        ),
    )

    assert report.missing_workers == ()
    assert report.startup_issue_workers == ("worker-3",)
    assert report.incomplete_workers == ("worker-3",)
    worker_readiness_layer = next(
        layer for layer in report.proof_layers if layer.name == "worker_readiness"
    )
    assert worker_readiness_layer.state == "failed"
    assert worker_readiness_layer.blocking is True
    assert "worker-3" in worker_readiness_layer.summary


def test_read_team_admin_aggregation_report_uses_local_startup_timing_log(
    monkeypatch,
    tmp_path: Path,
) -> None:
    logs_dir = tmp_path / ".omx" / "logs"
    logs_dir.mkdir(parents=True)
    log_payload = (
        '{"timestamp":"2026-05-07T15:34:29.842Z","event":"dispatch_result",'
        '"source":"team.runtime.startup-timing",'
        '"team":"alpha-team","result":"failed","phase":"ready_wait_end",'
        '"to_worker":"worker-3","pane_id":"%13"}\n'
    )
    (logs_dir / "team-delivery-2026-05-07.jsonl").write_text(log_payload)
    monkeypatch.chdir(tmp_path)

    async def fake_read_tasks(request):
        return TeamApiListTasksSnapshot(
            count=2,
            tasks=(
                TeamApiTaskSnapshot(
                    id="task-1",
                    subject="worker-1 handoff",
                    status="completed",
                    owner="worker-1",
                ),
                TeamApiTaskSnapshot(
                    id="task-2",
                    subject="worker-2 handoff",
                    status="completed",
                    owner="worker-2",
                ),
            ),
        )

    async def fake_read_events(request):
        return TeamApiReadEventsSnapshot(count=0, cursor="", events=())

    async def fake_read_worker_status(request):
        return TeamApiWorkerStatusSnapshot(
            worker=request.worker,
            state="unknown",
            updated_at="1970-01-01T00:00:00.000Z",
        )

    monkeypatch.setattr(
        team_admin_aggregation, "read_team_api_list_tasks", fake_read_tasks
    )
    monkeypatch.setattr(
        team_admin_aggregation, "read_team_api_read_events", fake_read_events
    )
    monkeypatch.setattr(
        team_admin_aggregation,
        "read_team_api_read_worker_status",
        fake_read_worker_status,
    )

    report = asyncio.run(
        read_team_admin_aggregation_report(
            TeamAdminAggregationReportRequest(
                team_name="alpha-team",
                ralph_prd_artifact=_prd_artifact(),
            )
        )
    )

    assert report.aggregation_state == "waiting_for_workers"
    assert report.missing_workers == ()
    assert report.startup_issue_workers == ("worker-3",)
    assert report.incomplete_workers == ("worker-3",)
    assert report.requires_human_review is False


def test_read_team_admin_aggregation_report_collects_worker_status_snapshots(
    monkeypatch,
) -> None:
    calls: list[tuple[str, str]] = []

    async def fake_read_tasks(request):
        calls.append(("list_tasks", request.team_name))
        return TeamApiListTasksSnapshot(
            count=3,
            tasks=(
                TeamApiTaskSnapshot(
                    id="task-1",
                    subject="worker-1 handoff",
                    status="completed",
                    owner="worker-1",
                ),
                TeamApiTaskSnapshot(
                    id="task-2",
                    subject="worker-2 handoff",
                    status="completed",
                    owner="worker-2",
                ),
                TeamApiTaskSnapshot(
                    id="task-3",
                    subject="worker-3 handoff",
                    status="completed",
                    owner="worker-3",
                ),
            ),
        )

    async def fake_read_events(request):
        calls.append(("read_events", request.team_name))
        return TeamApiReadEventsSnapshot(count=0, cursor="0", events=())

    async def fake_read_worker_status(request):
        calls.append(("read_worker_status", f"{request.team_name}:{request.worker}"))
        return TeamApiWorkerStatusSnapshot(
            worker=request.worker,
            state="idle",
            updated_at="2026-05-06T00:00:00Z",
        )

    monkeypatch.setattr(
        team_admin_aggregation,
        "read_team_api_list_tasks",
        fake_read_tasks,
    )
    monkeypatch.setattr(
        team_admin_aggregation,
        "read_team_api_read_events",
        fake_read_events,
    )
    monkeypatch.setattr(
        team_admin_aggregation,
        "read_team_api_read_worker_status",
        fake_read_worker_status,
    )

    report = asyncio.run(
        read_team_admin_aggregation_report(
            TeamAdminAggregationReportRequest(
                team_name="alpha-team",
                ralph_prd_artifact=_prd_artifact(),
            )
        )
    )

    assert report.aggregation_state == "ready_for_ralph_review"
    assert report.merge_ready is True
    assert calls == [
        ("list_tasks", "alpha-team"),
        ("read_events", "alpha-team"),
        ("read_worker_status", "alpha-team:worker-1"),
        ("read_worker_status", "alpha-team:worker-2"),
        ("read_worker_status", "alpha-team:worker-3"),
    ]


def test_write_team_admin_aggregation_report_artifact_writes_json(tmp_path) -> None:
    report = build_team_admin_aggregation_report(
        ralph_prd_artifact=_prd_artifact(),
        task_snapshot=TeamApiListTasksSnapshot(
            count=1,
            tasks=(
                TeamApiTaskSnapshot(
                    id="task-1",
                    subject="worker-1 handoff",
                    status="completed",
                    owner="worker-1",
                ),
            ),
        ),
        event_snapshot=TeamApiReadEventsSnapshot(count=0, cursor="0", events=()),
        worker_statuses=(
            TeamApiWorkerStatusSnapshot(
                worker="worker-1",
                state="idle",
                updated_at="2026-05-06T00:00:00Z",
            ),
        ),
    )
    output_path = tmp_path / "reports" / "team-admin-report.json"

    written_path = write_team_admin_aggregation_report_artifact(report, output_path)

    assert written_path == output_path
    assert '"admin_id": "team-admin"' in output_path.read_text()
    assert '"aggregation_state": "human_review_required"' in output_path.read_text()
