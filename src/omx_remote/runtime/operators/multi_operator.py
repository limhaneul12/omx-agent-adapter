from omx_remote.adapter_types.type_contract.operator_contract_type import (
    ACTIONABLE_NEXT_ACTIONS,
    ACTIVE_LOOP_STATES,
)
from omx_remote.runtime.status.runtime_mode_status import read_runtime_mode_status
from omx_remote.schemas.multi_operator.snapshot_schemas import (
    FlowInterventionRequest,
    FlowSelector,
    ManagedFlowIdCollection,
    ManagedFlowKind,
    ManagedInterventionAction,
    ManagedOmxFlow,
    ManagedOmxFlowCollection,
    ManagedOmxRepo,
    ManagedOmxRepoCollection,
    MultiOperatorSnapshot,
    MultiOperatorSnapshotReadRequest,
)
from omx_remote.schemas.operator.action_schemas import (
    OperatorActionResult,
    OperatorLane,
    OperatorLoopState,
    OperatorNextAction,
    OperatorRecoveryHint,
)
from omx_remote.schemas.runtime.status_schemas import (
    RuntimeModeStatusRequest,
    RuntimeModeStatusResult,
    RuntimeModeStatusSnapshot,
)
from omx_remote.schemas.teamwork.status_schemas import (
    TeamStatusRequest,
    TeamStatusSnapshot,
)
from omx_remote.teamwork.team_snapshot import read_team_status


def _build_observable_status_result(
    lane: OperatorLane,
    action: str,
    summary: str,
) -> OperatorActionResult:
    """Handles build observable status result.
    
    Args:
        lane [OperatorLane]: Function argument.
        action [str]: Function argument.
        summary [str]: Function argument.
    
    Returns:
        OperatorActionResult: Function return value.
    """
    result: OperatorActionResult = OperatorActionResult(
        lane=lane,
        action=action,
        loop_state=OperatorLoopState.SUCCESS,
        next_action=OperatorNextAction.OBSERVE,
        summary=summary,
    )
    return result



def _build_launchable_status_result(
    lane: OperatorLane,
    action: str,
    summary: str,
) -> OperatorActionResult:
    """Handles build launchable status result.
    
    Args:
        lane [OperatorLane]: Function argument.
        action [str]: Function argument.
        summary [str]: Function argument.
    
    Returns:
        OperatorActionResult: Function return value.
    """
    recovery_hint: OperatorRecoveryHint = OperatorRecoveryHint(
        next_action=OperatorNextAction.LAUNCH,
        reason="The live status surface did not report an active flow, so launch is the next safe action.",
    )
    result: OperatorActionResult = OperatorActionResult(
        lane=lane,
        action=action,
        loop_state=OperatorLoopState.NO_RESUMABLE_STATE_FAILURE,
        next_action=OperatorNextAction.LAUNCH,
        summary=summary,
        recovery_hint=recovery_hint,
    )
    return result



def _build_ralph_status_result(
    status_result: RuntimeModeStatusResult,
) -> OperatorActionResult:
    """Handles build ralph status result.
    
    Args:
        status_result [RuntimeModeStatusResult]: Function argument.
    
    Returns:
        OperatorActionResult: Function return value.
    """
    mode_snapshot: RuntimeModeStatusSnapshot | None = status_result.mode_snapshot
    if status_result.found and mode_snapshot is not None and mode_snapshot.is_active:
        summary: str = "ralph status is active from the live OMX runtime status surface."
        result: OperatorActionResult = _build_observable_status_result(
            lane=OperatorLane.RALPH,
            action="status",
            summary=summary,
        )
        return result

    inactive_summary: str = (
        "ralph status is not active from the live OMX runtime status surface."
    )
    result = _build_launchable_status_result(
        lane=OperatorLane.RALPH,
        action="status",
        summary=inactive_summary,
    )
    return result



def _team_status_is_active(team_status: TeamStatusSnapshot) -> bool:
    """Handles team status is active.
    
    Args:
        team_status [TeamStatusSnapshot]: Function argument.
    
    Returns:
        bool: Function return value.
    """
    normalized_status_text: str = team_status.status.strip().lower()
    phase_text: str | None = team_status.phase
    normalized_phase_text: str | None = None
    if phase_text is not None:
        normalized_phase_text = phase_text.strip().lower()

    if normalized_status_text in {"active", "running"}:
        status_is_active: bool = True
        return status_is_active

    if normalized_phase_text in {"active", "running", "starting"}:
        status_is_active = True
        return status_is_active

    status_is_active = False
    return status_is_active



def _build_team_status_result(team_status: TeamStatusSnapshot) -> OperatorActionResult:
    """Handles build team status result.
    
    Args:
        team_status [TeamStatusSnapshot]: Function argument.
    
    Returns:
        OperatorActionResult: Function return value.
    """
    if _team_status_is_active(team_status):
        summary: str = (
            f"team {team_status.team_name} status is active from the live OMX team status surface."
        )
        result: OperatorActionResult = _build_observable_status_result(
            lane=OperatorLane.TEAM,
            action="status",
            summary=summary,
        )
        return result

    inactive_summary: str = (
        f"team {team_status.team_name} status is not active from the live OMX team status surface."
    )
    result = _build_launchable_status_result(
        lane=OperatorLane.TEAM,
        action="status",
        summary=inactive_summary,
    )
    return result



async def read_live_multi_operator_snapshot(
    request: MultiOperatorSnapshotReadRequest,
) -> MultiOperatorSnapshot:
    """Read live Ralph/team status surfaces into one repo-scoped multi-operator snapshot.
    
    Args:
        request [MultiOperatorSnapshotReadRequest]: Function argument.
    
    Returns:
        MultiOperatorSnapshot: Function return value.
    """
    registry = MultiOperatorRegistry()
    registry.register_repo(
        ManagedOmxRepo(repo_id=request.repo_id, repo_root=request.repo_root)
    )
    registry.register_flow(
        ManagedOmxFlow(
            flow_id=f"{request.repo_id}:ralph",
            repo_id=request.repo_id,
            flow_kind=ManagedFlowKind.RALPH,
            flow_name="ralph",
        )
    )

    ralph_status_result: RuntimeModeStatusResult = await read_runtime_mode_status(
        RuntimeModeStatusRequest(mode="ralph")
    )
    ralph_operator_result: OperatorActionResult = _build_ralph_status_result(
        ralph_status_result
    )
    registry.update_flow_result(f"{request.repo_id}:ralph", ralph_operator_result)

    team_name: str
    for team_name in request.team_names:
        team_flow_id: str = f"{request.repo_id}:team-{team_name}"
        registry.register_flow(
            ManagedOmxFlow(
                flow_id=team_flow_id,
                repo_id=request.repo_id,
                flow_kind=ManagedFlowKind.TEAM,
                flow_name=f"team:{team_name}",
                team_name=team_name,
            )
        )
        team_status: TeamStatusSnapshot = await read_team_status(
            TeamStatusRequest(team_name=team_name)
        )
        team_operator_result: OperatorActionResult = _build_team_status_result(
            team_status
        )
        registry.update_flow_result(team_flow_id, team_operator_result)

    snapshot: MultiOperatorSnapshot = registry.summarize()
    return snapshot



class MultiOperatorRegistry:
    """Track repo-scoped OMX flows and summarize their current operator states."""

    def __init__(self) -> None:
        """Initializes the object.
        """
        self._repos: dict[str, ManagedOmxRepo] = {}
        self._flows: dict[str, ManagedOmxFlow] = {}

    def register_repo(self, repo: ManagedOmxRepo) -> None:
        """Register one repo-scoped OMX workspace.

        Args:
            repo [ManagedOmxRepo]: Typed repo handle to store in the registry.
        """
        self._repos[repo.repo_id] = repo

    def register_flow(self, flow: ManagedOmxFlow) -> None:
        """Register one controllable OMX-backed flow.

        Args:
            flow [ManagedOmxFlow]: Typed flow handle to store in the registry.

        Raises:
            ValueError: If the parent repo was not registered first.
        """
        if flow.repo_id not in self._repos:
            raise ValueError(
                f"Cannot register flow '{flow.flow_id}' because repo '{flow.repo_id}' is unknown."
            )

        self._flows[flow.flow_id] = flow

    def update_flow_result(self, flow_id: str, result: OperatorActionResult) -> None:
        """Attach one latest operator-loop result to a registered flow.

        Args:
            flow_id [str]: Registered flow id to update.
            result [OperatorActionResult]: Latest typed loop result for that flow.

        Raises:
            ValueError: If the flow id is unknown.
        """
        existing_flow: ManagedOmxFlow | None = self._flows.get(flow_id)
        if existing_flow is None:
            raise ValueError(f"Cannot update unknown flow '{flow_id}'.")

        updated_flow: ManagedOmxFlow = existing_flow.model_copy(
            update={"last_result": result}
        )
        self._flows[flow_id] = updated_flow

    def summarize(self) -> MultiOperatorSnapshot:
        """Build one aggregated snapshot across all registered repos and flows.

        Returns:
            MultiOperatorSnapshot: Typed snapshot for the current registry state.
        """
        active_flow_ids: list[str] = []
        launchable_flow_ids: list[str] = []
        resumable_flow_ids: list[str] = []
        cleanup_flow_ids: list[str] = []
        terminal_flow_ids: list[str] = []

        flow: ManagedOmxFlow
        for flow in self._flows.values():
            flow_result: OperatorActionResult | None = flow.last_result
            if flow_result is None:
                continue

            if flow_result.loop_state in ACTIVE_LOOP_STATES:
                active_flow_ids.append(flow.flow_id)

            if flow_result.next_action == OperatorNextAction.LAUNCH:
                launchable_flow_ids.append(flow.flow_id)
            elif flow_result.next_action == OperatorNextAction.RESUME:
                resumable_flow_ids.append(flow.flow_id)
            elif flow_result.next_action == OperatorNextAction.CLEANUP:
                cleanup_flow_ids.append(flow.flow_id)
            elif flow_result.loop_state == OperatorLoopState.TERMINAL_FAILURE:
                terminal_flow_ids.append(flow.flow_id)

        repo_collection: ManagedOmxRepoCollection = ManagedOmxRepoCollection(
            root=tuple(self._repos.values())
        )
        flow_collection: ManagedOmxFlowCollection = ManagedOmxFlowCollection(
            root=tuple(self._flows.values())
        )
        active_flow_collection: ManagedFlowIdCollection = ManagedFlowIdCollection(
            root=tuple(active_flow_ids)
        )
        launchable_flow_collection: ManagedFlowIdCollection = ManagedFlowIdCollection(
            root=tuple(launchable_flow_ids)
        )
        resumable_flow_collection: ManagedFlowIdCollection = ManagedFlowIdCollection(
            root=tuple(resumable_flow_ids)
        )
        cleanup_flow_collection: ManagedFlowIdCollection = ManagedFlowIdCollection(
            root=tuple(cleanup_flow_ids)
        )
        terminal_flow_collection: ManagedFlowIdCollection = ManagedFlowIdCollection(
            root=tuple(terminal_flow_ids)
        )
        snapshot: MultiOperatorSnapshot = MultiOperatorSnapshot(
            repos=repo_collection,
            flows=flow_collection,
            active_flow_ids=active_flow_collection,
            launchable_flow_ids=launchable_flow_collection,
            resumable_flow_ids=resumable_flow_collection,
            cleanup_flow_ids=cleanup_flow_collection,
            terminal_flow_ids=terminal_flow_collection,
        )
        return snapshot

    def build_flow_intervention_request(
        self,
        flow_id: str,
    ) -> FlowInterventionRequest | None:
        """Build one typed intervention request from the latest registered next action.

        Args:
            flow_id [str]: Registered flow id to inspect.

        Returns:
            FlowInterventionRequest | None: Typed intervention request when the next action is actionable, otherwise `None`.

        Raises:
            ValueError: If the flow id is unknown.
        """
        existing_flow: ManagedOmxFlow | None = self._flows.get(flow_id)
        if existing_flow is None:
            raise ValueError(f"Cannot build intervention for unknown flow '{flow_id}'.")

        flow_result: OperatorActionResult | None = existing_flow.last_result
        if flow_result is None:
            return None

        next_action: OperatorNextAction = flow_result.next_action
        if next_action not in ACTIONABLE_NEXT_ACTIONS:
            return None

        requested_action: ManagedInterventionAction
        if next_action == OperatorNextAction.LAUNCH:
            requested_action = ManagedInterventionAction.LAUNCH
        elif next_action == OperatorNextAction.RESUME:
            requested_action = ManagedInterventionAction.RESUME
        elif next_action == OperatorNextAction.RETRY:
            requested_action = ManagedInterventionAction.RETRY
        elif next_action == OperatorNextAction.CLEANUP:
            requested_action = ManagedInterventionAction.CLEANUP
        elif next_action == OperatorNextAction.CANCEL:
            requested_action = ManagedInterventionAction.CANCEL
        else:
            requested_action = ManagedInterventionAction.ESCALATE

        intervention_request: FlowInterventionRequest = FlowInterventionRequest(
            selector=FlowSelector(
                repo_id=existing_flow.repo_id,
                flow_id=existing_flow.flow_id,
            ),
            requested_action=requested_action,
        )
        return intervention_request
