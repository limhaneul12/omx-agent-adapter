from __future__ import annotations

from dataclasses import dataclass

from comx_harness.ade.controller import AdeController
from comx_harness.ade.state_store import AdeStateStore
from comx_harness.ade.tk_runtime_helpers import provider_readiness_label
from comx_harness.ade.tk_shell import AdeTkShell
from comx_harness.ade.workspace_service import WorkspaceService
from comx_harness.schemas.ade_operator_schemas import (
    AttentionTarget,
    WorkspaceRunProjection,
)
from comx_harness.schemas.ade_schemas import (
    AdeCatalog,
    WorkspaceRecord,
    WorkspaceStatus,
)
from comx_harness.schemas.provider_schemas import CapabilityReport
from comx_harness.schemas.strategy_schemas import (
    StrategyRecord,
    StrategyStage,
    StrategyStageRecord,
)
from comx_harness.shared.harness_enums.lifecycle_enums import (
    ProcessLiveness,
    RunStatus,
)
from comx_harness.shared.harness_enums.operator_enums import AttentionKind
from comx_harness.storage.strategy_store import StrategyStore
from comx_harness.storage.workspace_layout import WorkspaceLayout


@dataclass(frozen=True, slots=True)
class AttentionSelection:
    workspace: WorkspaceRecord
    run_id: str
    target: AttentionTarget


@dataclass(frozen=True, slots=True)
class AttentionRefreshEntry:
    kind: AttentionKind
    workspace_name: str
    message: str
    selection: AttentionSelection


@dataclass(frozen=True, slots=True)
class AdeRefreshSnapshot:
    active_workspace_id: str | None
    catalog: AdeCatalog
    workspace_statuses: tuple[WorkspaceStatus, ...]
    active_status: WorkspaceStatus | None
    active_projection: WorkspaceRunProjection | None
    active_strategies: tuple[StrategyRecord, ...]
    attention: tuple[AttentionRefreshEntry, ...]
    capabilities: CapabilityReport | None
    capability_error: str | None


class AdeRefreshReader:
    """Collect one immutable ADE projection without touching Tk widgets."""

    def __init__(self, store: AdeStateStore) -> None:
        self._store = store
        self._workspaces = WorkspaceService(store)

    def read(
        self,
        active_workspace_id: str | None,
        reviewed_run_ids: tuple[str, ...],
    ) -> AdeRefreshSnapshot:
        catalog = self._store.load_catalog()
        reviewed = set(reviewed_run_ids)
        statuses: list[WorkspaceStatus] = []
        attention: list[AttentionRefreshEntry] = []
        active_status: WorkspaceStatus | None = None
        active_projection: WorkspaceRunProjection | None = None
        active_strategies: tuple[StrategyRecord, ...] = ()
        active_controller: AdeController | None = None
        for workspace in catalog.workspaces:
            status = self._workspaces.inspect_workspace(workspace.workspace_id)
            controller = AdeController(workspace.root_path, self._store.state_root)
            projection = controller.observe.projection()
            statuses.append(status)
            attention.extend(
                _attention_entries(
                    workspace=workspace,
                    projection=projection,
                    reviewed_run_ids=reviewed,
                )
            )
            if workspace.workspace_id == active_workspace_id:
                active_status = status
                active_projection = projection
                active_strategies = StrategyStore(
                    WorkspaceLayout.from_workspace(workspace.root_path)
                ).list_records()
                active_controller = controller
        capabilities: CapabilityReport | None = None
        capability_error: str | None = None
        if active_controller is not None:
            try:
                capabilities = active_controller.observe.capabilities()
            except (OSError, ValueError) as error:
                capability_error = str(error) or type(error).__name__
        snapshot = AdeRefreshSnapshot(
            active_workspace_id=active_workspace_id,
            catalog=catalog,
            workspace_statuses=tuple(statuses),
            active_status=active_status,
            active_projection=active_projection,
            active_strategies=active_strategies,
            attention=tuple(attention),
            capabilities=capabilities,
            capability_error=capability_error,
        )
        return snapshot


class AdeRefreshRenderer:
    """Apply an immutable refresh snapshot only from the Tk event-loop thread."""

    def __init__(self, ui: AdeTkShell) -> None:
        self._ui = ui

    def apply(
        self,
        snapshot: AdeRefreshSnapshot,
        active_workspace: WorkspaceRecord,
        selected_run_id: str | None,
    ) -> None:
        self._render_sidebar(snapshot, active_workspace=active_workspace)
        self._render_workspace(snapshot, selected_run_id=selected_run_id)
        self._render_strategies(snapshot)
        self._render_capabilities(snapshot)

    def _render_sidebar(
        self,
        snapshot: AdeRefreshSnapshot,
        active_workspace: WorkspaceRecord,
    ) -> None:
        statuses = {
            status.workspace.workspace_id: status
            for status in snapshot.workspace_statuses
        }
        self._ui.sidebar.delete(*self._ui.sidebar.get_children())
        for project in snapshot.catalog.projects:
            parent = f"project:{project.project_id}"
            self._ui.sidebar.insert(
                "",
                "end",
                iid=parent,
                text=project.name,
                open=True,
            )
            for workspace in snapshot.catalog.workspaces:
                if workspace.project_id != project.project_id:
                    continue
                status = statuses[workspace.workspace_id]
                label = (
                    f"{workspace.name} · {status.branch or 'not-git'}"
                    f"{' • dirty' if status.dirty else ''}"
                    f"{' • missing' if status.missing else ''}"
                )
                self._ui.sidebar.insert(
                    parent,
                    "end",
                    iid=f"workspace:{workspace.workspace_id}",
                    text=label,
                )
        selected = f"workspace:{active_workspace.workspace_id}"
        if self._ui.sidebar.exists(selected):
            self._ui.sidebar.selection_set(selected)

    def _render_workspace(
        self,
        snapshot: AdeRefreshSnapshot,
        selected_run_id: str | None,
    ) -> None:
        status = snapshot.active_status
        projection = snapshot.active_projection
        if status is None or projection is None:
            return
        cleanliness = (
            "dirty"
            if status.dirty
            else "clean"
            if status.dirty is not None
            else "unknown"
        )
        self._ui.workspace_summary.set(
            f"{status.branch or 'not a Git repository'} · {cleanliness}"
        )
        self._render_metrics(projection)
        self._ui.runs.delete(*self._ui.runs.get_children())
        for run in projection.runs:
            self._ui.runs.insert(
                "",
                "end",
                iid=run.run_id,
                values=(
                    run.status,
                    run.provider,
                    run.liveness,
                    _run_objective_label(run.objective),
                ),
                tags=(_run_state_tag(run.status, run.liveness),),
            )
        if selected_run_id and self._ui.runs.exists(selected_run_id):
            self._ui.runs.selection_set(selected_run_id)

    def _render_strategies(self, snapshot: AdeRefreshSnapshot) -> None:
        self._ui.strategies.delete(*self._ui.strategies.get_children())
        for record in snapshot.active_strategies:
            strategy_id = record.definition.strategy_id
            parent = f"strategy:{strategy_id}"
            self._ui.strategies.insert(
                "",
                "end",
                iid=parent,
                text=strategy_id,
                open=True,
                values=(
                    record.status,
                    record.current_stage_id or "",
                    "",
                    "",
                    record.definition.mission,
                    _strategy_evidence_label(record),
                ),
                tags=(str(record.status),),
            )
            definitions = {stage.stage_id: stage for stage in record.definition.stages}
            for stage_record in record.stages:
                definition = definitions[stage_record.stage_id]
                self._ui.strategies.insert(
                    parent,
                    "end",
                    iid=f"strategy-stage:{strategy_id}:{stage_record.stage_id}",
                    text=stage_record.stage_id,
                    values=(
                        stage_record.status,
                        stage_record.node_type,
                        stage_record.provider or "",
                        _stage_surface_label(definition),
                        stage_record.run_id or stage_record.handoff_id or "unobserved",
                        _stage_evidence_label(stage_record),
                    ),
                    tags=(str(stage_record.status),),
                )

    def _render_capabilities(self, snapshot: AdeRefreshSnapshot) -> None:
        report = snapshot.capabilities
        if report is None:
            detail = snapshot.capability_error or "no active Workspace"
            self._ui.capability_label.configure(
                text=f"Providers: unavailable ({detail})"
            )
            return
        self._ui.capability_label.configure(
            text=f"Providers · {provider_readiness_label(report)}"
        )

    def _render_metrics(self, projection: WorkspaceRunProjection) -> None:
        active = sum(
            run.status == RunStatus.RUNNING and run.liveness == ProcessLiveness.RUNNING
            for run in projection.runs
        )
        attention = sum(len(run.attention) for run in projection.runs)
        completed = sum(run.status == RunStatus.SUCCEEDED for run in projection.runs)
        self._ui.active_count.set(str(active))
        self._ui.attention_count.set(str(attention))
        self._ui.completed_count.set(str(completed))


def _attention_entries(
    workspace: WorkspaceRecord,
    projection: WorkspaceRunProjection,
    reviewed_run_ids: set[str],
) -> tuple[AttentionRefreshEntry, ...]:
    entries: list[AttentionRefreshEntry] = []
    for run in projection.runs:
        for item in run.attention:
            kind = AttentionKind(item.kind)
            if (
                run.run_id in reviewed_run_ids
                and kind == AttentionKind.READY_FOR_REVIEW
            ):
                continue
            entries.append(
                AttentionRefreshEntry(
                    kind=kind,
                    workspace_name=workspace.name,
                    message=item.message,
                    selection=AttentionSelection(
                        workspace=workspace,
                        run_id=run.run_id,
                        target=item.target,
                    ),
                )
            )
    return tuple(entries)


def _run_state_tag(status: RunStatus, liveness: ProcessLiveness) -> str:
    if status == RunStatus.RUNNING and liveness == ProcessLiveness.RUNNING:
        return "working"
    if status in {RunStatus.BLOCKED, RunStatus.STALE}:
        return "attention"
    if status == RunStatus.SUCCEEDED:
        return "succeeded"
    if status in {RunStatus.FAILED, RunStatus.CANCELLED}:
        return "failed"
    return ""


def _run_objective_label(objective: str) -> str:
    label = " ".join(objective.split())
    return label


def _stage_surface_label(stage: StrategyStage) -> str:
    return stage.workflow or stage.native_surface or str(stage.node_type)


def _stage_evidence_label(stage: StrategyStageRecord) -> str:
    if not stage.evidence:
        return stage.failure or "no evidence yet"
    passed = sum(item.passed for item in stage.evidence)
    failed = len(stage.evidence) - passed
    label = f"{passed} passed"
    if failed:
        label = f"{label} · {failed} failed"
    if stage.failure:
        label = f"{label} · {stage.failure}"
    return label


def _strategy_evidence_label(record: StrategyRecord) -> str:
    observed = sum(len(stage.evidence) for stage in record.stages)
    failed = sum(not item.passed for stage in record.stages for item in stage.evidence)
    if observed == 0:
        return "no evidence yet"
    return f"{observed - failed}/{observed} evidence passed"
