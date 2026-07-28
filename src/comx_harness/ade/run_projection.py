from __future__ import annotations

import re
from pathlib import Path

from comx_harness.ade.omx_team_native import OmxTeamObserver
from comx_harness.controller_surface import HarnessTools
from comx_harness.schemas.ade_operator_schemas import (
    AttentionItem,
    AttentionTarget,
    RunSummary,
    WorkspaceRunProjection,
)
from comx_harness.schemas.artifact_schemas import VerifiedArtifact
from comx_harness.schemas.execution_schemas import RunReference
from comx_harness.schemas.lifecycle_schemas import EventReport, RunEvent, RunState
from comx_harness.schemas.omx_team_schemas import OmxTeamProjection
from comx_harness.shared.harness_enums.lifecycle_enums import (
    ProcessLiveness,
    RunStatus,
)
from comx_harness.shared.harness_enums.operator_enums import (
    AgentStatus,
    AttentionEntityKind,
    AttentionKind,
    RunDetailTab,
)
from comx_harness.storage.workspace_layout import WorkspaceLayout

_EVENT_TYPE_TOKEN = re.compile(r"[a-z0-9]+")
_EVENT_ACTION_TOKENS = frozenset(
    {
        "awaiting",
        "needed",
        "needs",
        "pending",
        "request",
        "requested",
        "required",
        "requires",
        "waiting",
    }
)


class WorkspaceRunProjectionReader:
    """Build a read-only operator projection from durable Run state."""

    def __init__(
        self,
        tools: HarnessTools | None = None,
        *,
        team_observer: OmxTeamObserver | None = None,
    ) -> None:
        self.tools = tools or HarnessTools()
        self.team_observer = team_observer

    def read(
        self,
        workspace: str | Path,
        *,
        limit: int = 25,
    ) -> WorkspaceRunProjection:
        if limit < 1:
            raise ValueError("limit must be positive")
        layout = WorkspaceLayout.from_workspace(workspace)
        run_ids = self._recent_run_ids(layout, limit=limit)
        summaries: list[RunSummary] = []
        for run_id in run_ids:
            try:
                state = self.tools.status(
                    RunReference(workspace=str(layout.workspace), run_id=run_id)
                )
            except (FileNotFoundError, OSError, ValueError):
                continue
            reference = RunReference(
                workspace=str(layout.workspace),
                run_id=run_id,
            )
            events = self._events(reference)
            artifacts = self._artifacts(reference, state)
            teams = self._teams(events)
            summaries.append(
                self._summary(
                    state,
                    events=events,
                    artifacts=artifacts,
                    teams=teams,
                )
            )
        projection = WorkspaceRunProjection(
            workspace=str(layout.workspace),
            runs=tuple(summaries),
        )
        return projection

    @staticmethod
    def _recent_run_ids(layout: WorkspaceLayout, *, limit: int) -> tuple[str, ...]:
        if not layout.runs_root.exists():
            return ()
        candidates = [
            path
            for path in layout.runs_root.iterdir()
            if path.is_dir() and (path / "run.json").is_file()
        ]
        candidates.sort(
            key=lambda path: (path / "run.json").stat().st_mtime_ns,
            reverse=True,
        )
        return tuple(path.name for path in candidates[:limit])

    def _events(self, reference: RunReference) -> tuple[RunEvent, ...]:
        try:
            return self.tools.events(reference).events
        except (FileNotFoundError, OSError, ValueError):
            return ()

    def _artifacts(
        self,
        reference: RunReference,
        state: RunState,
    ) -> tuple[VerifiedArtifact, ...]:
        try:
            return self.tools.artifacts(reference).artifacts
        except (FileNotFoundError, OSError, ValueError):
            return state.record.verified_artifacts

    def _teams(self, events: tuple[RunEvent, ...]) -> tuple[OmxTeamProjection, ...]:
        observer = self.team_observer
        if observer is None or not events:
            return ()
        report = EventReport(run_id=events[0].run_id, events=events)
        for name in observer.discover(report):
            team = observer.read(name)
            if team.available:
                return (team,)
        return ()

    @staticmethod
    def _summary(
        state: RunState,
        *,
        events: tuple[RunEvent, ...],
        artifacts: tuple[VerifiedArtifact, ...],
        teams: tuple[OmxTeamProjection, ...],
    ) -> RunSummary:
        record = state.record
        return RunSummary(
            run_id=record.run_id,
            provider=record.provider,
            objective=record.objective,
            status=record.status,
            liveness=state.liveness,
            started_at=record.started_at,
            finished_at=record.finished_at,
            parent_run_id=record.parent_run_id,
            verified_artifact_count=len(record.verified_artifacts),
            attention=_attention_items(
                state,
                events=events,
                artifacts=artifacts,
                teams=teams,
            ),
        )


def _attention_items(
    state: RunState,
    *,
    events: tuple[RunEvent, ...],
    artifacts: tuple[VerifiedArtifact, ...],
    teams: tuple[OmxTeamProjection, ...],
) -> tuple[AttentionItem, ...]:
    record = state.record
    items = (
        list(_event_attention(events))
        if record.status in {RunStatus.RUNNING, RunStatus.BLOCKED}
        else []
    )
    if record.status == RunStatus.BLOCKED:
        items.append(
            AttentionItem(
                kind=AttentionKind.BLOCKED,
                message=record.failure.message if record.failure else "Run is blocked.",
                evidence=_failure_evidence(state),
                target=_run_target(record.run_id, RunDetailTab.OVERVIEW),
            )
        )
    if record.status == RunStatus.FAILED:
        tab = (
            RunDetailTab.EVIDENCE
            if record.failure
            and any(
                marker in record.failure.code.casefold()
                for marker in ("verification", "artifact", "evidence")
            )
            else RunDetailTab.OVERVIEW
        )
        items.append(
            AttentionItem(
                kind=AttentionKind.FAILED,
                message=record.failure.message if record.failure else "Run failed.",
                evidence=_failure_evidence(state),
                target=_run_target(record.run_id, tab),
            )
        )
    if record.status == RunStatus.STALE or (
        record.status == RunStatus.RUNNING and state.liveness == ProcessLiveness.MISSING
    ):
        items.append(
            AttentionItem(
                kind=AttentionKind.STALE,
                message=(
                    record.failure.message
                    if record.failure
                    else "Recorded process is missing or stale."
                ),
                evidence=f"status={record.status}; liveness={state.liveness}",
                target=_run_target(record.run_id, RunDetailTab.OVERVIEW),
            )
        )
    items.extend(_team_attention(teams))
    items.extend(_artifact_attention(artifacts))
    if record.status == RunStatus.SUCCEEDED:
        review_artifact = next(
            (
                artifact
                for artifact in artifacts
                if artifact.kind == "result" and artifact.exists
            ),
            None,
        )
        items.append(
            AttentionItem(
                kind=AttentionKind.READY_FOR_REVIEW,
                message="Verified result awaits review.",
                evidence=(
                    f"verified result artifact: {review_artifact.path}"
                    if review_artifact
                    else f"run status={record.status}"
                ),
                target=(
                    AttentionTarget(
                        tab=RunDetailTab.ARTIFACTS,
                        entity_kind=AttentionEntityKind.ARTIFACT,
                        entity_id=review_artifact.path,
                    )
                    if review_artifact
                    else _run_target(record.run_id, RunDetailTab.EVIDENCE)
                ),
            )
        )
    return tuple(items)


def _event_attention(events: tuple[RunEvent, ...]) -> tuple[AttentionItem, ...]:
    pending: list[tuple[RunEvent, AttentionKind, str]] = []
    for event in reversed(events):
        event_type = event.provider_event_type
        if event_type is None:
            continue
        tokens = set(_EVENT_TYPE_TOKEN.findall(event_type.casefold()))
        if tokens & {"approval", "permission"} and tokens & _EVENT_ACTION_TOKENS:
            kind = AttentionKind.APPROVAL_REQUIRED
            message = "Provider requires operator approval."
        elif tokens & {"input", "question", "prompt"} and tokens & _EVENT_ACTION_TOKENS:
            kind = AttentionKind.INPUT_REQUIRED
            message = "Provider is waiting for operator input."
        else:
            break
        pending.append((event, kind, message))
    return tuple(
        AttentionItem(
            kind=kind,
            message=message,
            evidence=f"provider event {event.sequence}: {event.provider_event_type}",
            target=AttentionTarget(
                tab=RunDetailTab.ACTIVITY,
                entity_kind=AttentionEntityKind.EVENT,
                entity_id=f"{event.sequence:04d}",
            ),
        )
        for event, kind, message in reversed(pending)
    )


def _team_attention(
    teams: tuple[OmxTeamProjection, ...],
) -> tuple[AttentionItem, ...]:
    items: list[AttentionItem] = []
    for team in teams:
        for worker in team.workers:
            if (
                worker.state not in {AgentStatus.BLOCKED, AgentStatus.FAILED}
                and worker.alive is not False
                and worker.name not in team.non_reporting_workers
            ):
                continue
            items.append(
                AttentionItem(
                    kind=(
                        AttentionKind.FAILED
                        if worker.state == AgentStatus.FAILED
                        else AttentionKind.BLOCKED
                    ),
                    message=f"Agent {worker.name} requires review.",
                    evidence=(
                        f"team={team.team_name}; state={worker.state}; "
                        f"alive={worker.alive}"
                    ),
                    target=AttentionTarget(
                        tab=RunDetailTab.AGENTS,
                        entity_kind=AttentionEntityKind.AGENT,
                        entity_id=worker.name,
                    ),
                )
            )
        for task in team.tasks:
            if task.status not in {"blocked", "failed"}:
                continue
            items.append(
                AttentionItem(
                    kind=(
                        AttentionKind.FAILED
                        if task.status == "failed"
                        else AttentionKind.BLOCKED
                    ),
                    message=f"Task {task.task_id} is {task.status}.",
                    evidence=f"team={team.team_name}; task_status={task.status}",
                    target=AttentionTarget(
                        tab=RunDetailTab.TASKS,
                        entity_kind=AttentionEntityKind.TASK,
                        entity_id=task.task_id,
                    ),
                )
            )
    return tuple(items)


def _artifact_attention(
    artifacts: tuple[VerifiedArtifact, ...],
) -> tuple[AttentionItem, ...]:
    return tuple(
        AttentionItem(
            kind=AttentionKind.ARTIFACT_ISSUE,
            message=f"Required Artifact is missing or empty: {artifact.path}",
            evidence=(
                f"required={artifact.required}; exists={artifact.exists}; "
                f"size_bytes={artifact.size_bytes}"
            ),
            target=AttentionTarget(
                tab=RunDetailTab.ARTIFACTS,
                entity_kind=AttentionEntityKind.ARTIFACT,
                entity_id=artifact.path,
            ),
        )
        for artifact in artifacts
        if artifact.required and (not artifact.exists or artifact.size_bytes == 0)
    )


def _run_target(run_id: str, tab: RunDetailTab) -> AttentionTarget:
    return AttentionTarget(
        tab=tab,
        entity_kind=AttentionEntityKind.RUN,
        entity_id=run_id,
    )


def _failure_evidence(state: RunState) -> str:
    failure = state.record.failure
    return (
        f"failure={failure.code}; status={state.record.status}"
        if failure
        else f"status={state.record.status}; liveness={state.liveness}"
    )
