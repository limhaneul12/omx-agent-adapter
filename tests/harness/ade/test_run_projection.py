from pathlib import Path
from unittest.mock import MagicMock

from comx_harness.ade.run_projection import WorkspaceRunProjectionReader
from comx_harness.controller_surface import HarnessTools
from comx_harness.schemas.artifact_schemas import ArtifactReport, VerifiedArtifact
from comx_harness.schemas.lifecycle_schemas import (
    EventReport,
    RunEvent,
    RunFailure,
    RunRecord,
    RunState,
)
from comx_harness.schemas.omx_team_schemas import (
    OmxTaskProjection,
    OmxTeamProjection,
    OmxWorkerProjection,
)
from comx_harness.shared.harness_enums.lifecycle_enums import (
    EventKind,
    ProcessLiveness,
    RunStatus,
)
from comx_harness.shared.harness_enums.operator_enums import (
    AgentStatus,
    AttentionEntityKind,
    AttentionKind,
    RunDetailTab,
)
from comx_harness.shared.harness_enums.provider_enums import ProviderId
from comx_harness.storage.run_store import RunStore
from comx_harness.storage.workspace_layout import WorkspaceLayout


def _store_record(workspace: Path, record: RunRecord) -> Path:
    layout = WorkspaceLayout.from_workspace(workspace)
    store = RunStore(layout)
    store.ensure_run(record.run_id)
    return store.write_record(record)


def test_projection_reads_recent_runs_and_attention(tmp_path: Path) -> None:
    _store_record(
        tmp_path,
        RunRecord(
            run_id="run-success",
            owner_controller_id="human-operator",
            provider=ProviderId.CODEX,
            objective="Review repository",
            status=RunStatus.SUCCEEDED,
            plan_path="plan.json",
            finished_at="2026-07-28T00:00:00Z",
        ),
    )
    _store_record(
        tmp_path,
        RunRecord(
            run_id="run-failed",
            owner_controller_id="human-operator",
            provider=ProviderId.OMX,
            objective="Implement goal",
            status=RunStatus.FAILED,
            plan_path="plan.json",
            finished_at="2026-07-28T00:01:00Z",
            failure=RunFailure(code="verification_failed", message="Tests failed."),
        ),
    )

    projection = WorkspaceRunProjectionReader().read(tmp_path)

    assert [run.run_id for run in projection.runs] == ["run-failed", "run-success"]
    assert projection.runs[0].attention[0].kind == AttentionKind.FAILED
    assert projection.runs[1].attention[0].kind == AttentionKind.READY_FOR_REVIEW


def test_projection_returns_empty_for_new_workspace(tmp_path: Path) -> None:
    projection = WorkspaceRunProjectionReader().read(tmp_path)

    assert projection.workspace == str(tmp_path.resolve())
    assert projection.runs == ()


def test_projection_targets_actionable_native_and_artifact_evidence(
    tmp_path: Path,
) -> None:
    record = RunRecord(
        run_id="run-attention",
        owner_controller_id="human-operator",
        provider=ProviderId.OMX,
        objective="Operate native team",
        status=RunStatus.RUNNING,
        plan_path="plan.json",
    )
    _store_record(tmp_path, record)
    tools = MagicMock(spec=HarnessTools)
    tools.status.return_value = RunState(
        record=record,
        liveness=ProcessLiveness.RUNNING,
    )
    tools.events.return_value = EventReport(
        run_id=record.run_id,
        events=(
            RunEvent(
                run_id=record.run_id,
                sequence=7,
                timestamp="2026-07-28T00:00:00Z",
                kind=EventKind.PROVIDER,
                message="approval.requested",
                provider_event_type="approval.requested",
                provider_payload_json='{"team_name":"alpha-team"}',
            ),
            RunEvent(
                run_id=record.run_id,
                sequence=8,
                timestamp="2026-07-28T00:00:01Z",
                kind=EventKind.PROVIDER,
                message="input.required",
                provider_event_type="input.required",
            ),
        ),
    )
    artifact_path = str(tmp_path / "verification.md")
    tools.artifacts.return_value = ArtifactReport(
        run_id=record.run_id,
        artifacts=(
            VerifiedArtifact(
                kind="expected",
                path=artifact_path,
                required=True,
                exists=False,
                size_bytes=0,
                source_run_id=record.run_id,
                source_provider=ProviderId.OMX,
            ),
        ),
    )
    observer = MagicMock()
    observer.discover.return_value = ("alpha-team",)
    observer.read.return_value = OmxTeamProjection(
        team_name="alpha-team",
        status="running",
        available=True,
        detail="Native OMX Team API evidence.",
        workers=(
            OmxWorkerProjection(
                name="worker-2",
                role="executor",
                state=AgentStatus.BLOCKED,
                alive=False,
            ),
        ),
        tasks=(
            OmxTaskProjection(
                task_id="2",
                subject="Verify",
                status="blocked",
                owner="worker-2",
            ),
        ),
    )

    projection = WorkspaceRunProjectionReader(
        tools,
        team_observer=observer,
    ).read(tmp_path)

    attention = projection.runs[0].attention
    targets = {
        (
            item.kind,
            item.target.tab,
            item.target.entity_kind,
            item.target.entity_id,
        )
        for item in attention
    }
    assert (
        AttentionKind.APPROVAL_REQUIRED,
        RunDetailTab.ACTIVITY,
        AttentionEntityKind.EVENT,
        "0007",
    ) in targets
    assert (
        AttentionKind.INPUT_REQUIRED,
        RunDetailTab.ACTIVITY,
        AttentionEntityKind.EVENT,
        "0008",
    ) in targets
    assert (
        AttentionKind.BLOCKED,
        RunDetailTab.AGENTS,
        AttentionEntityKind.AGENT,
        "worker-2",
    ) in targets
    assert (
        AttentionKind.BLOCKED,
        RunDetailTab.TASKS,
        AttentionEntityKind.TASK,
        "2",
    ) in targets
    assert (
        AttentionKind.ARTIFACT_ISSUE,
        RunDetailTab.ARTIFACTS,
        AttentionEntityKind.ARTIFACT,
        artifact_path,
    ) in targets
    assert all(item.evidence for item in attention)


def test_projection_does_not_invent_native_attention_when_team_is_unavailable(
    tmp_path: Path,
) -> None:
    record = RunRecord(
        run_id="run-unknown-team",
        owner_controller_id="human-operator",
        provider=ProviderId.OMX,
        objective="Observe team",
        status=RunStatus.RUNNING,
        plan_path="plan.json",
    )
    _store_record(tmp_path, record)
    tools = MagicMock(spec=HarnessTools)
    tools.status.return_value = RunState(
        record=record,
        liveness=ProcessLiveness.RUNNING,
    )
    tools.events.return_value = EventReport(
        run_id=record.run_id,
        events=(
            RunEvent(
                run_id=record.run_id,
                sequence=1,
                timestamp="2026-07-28T00:00:00Z",
                kind=EventKind.PROVIDER,
                message="approval.requested",
                provider_event_type="approval.requested",
            ),
            RunEvent(
                run_id=record.run_id,
                sequence=2,
                timestamp="2026-07-28T00:00:01Z",
                kind=EventKind.PROVIDER,
                message="team.started",
                provider_event_type="team.started",
                provider_payload_json='{"team_name":"missing-team"}',
            ),
        ),
    )
    tools.artifacts.return_value = ArtifactReport(run_id=record.run_id, artifacts=())
    observer = MagicMock()
    observer.discover.return_value = ("missing-team",)
    observer.read.return_value = OmxTeamProjection(
        team_name="missing-team",
        status="unavailable",
        available=False,
        detail="Native OMX reports that the team is missing.",
    )

    projection = WorkspaceRunProjectionReader(
        tools,
        team_observer=observer,
    ).read(tmp_path)

    assert projection.runs[0].attention == ()
    observer.read.assert_called_once_with("missing-team")
