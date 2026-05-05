import json
from pathlib import Path

import pytest

import omx_remote.runtime.codex_goal_supervisor as codex_goal_supervisor
from pydantic import ValidationError

from omx_remote.runtime.codex_goal_supervisor import (
    advance_tracked_codex_goal,
    build_codex_goal_snapshot,
    build_goal_to_ralph_handoff_prompt,
    dispatch_goal_delegation,
    prepare_tracked_codex_goal_ralph_handoff_prompt,
    select_goal_delegation,
)
from omx_remote.schemas.codex_goal import (
    CodexGoalAdvanceRequest,
    CodexGoalCapabilitySnapshot,
    CodexGoalMirrorState,
    CodexGoalSnapshot,
    GoalDelegationDecision,
    GoalDelegationDispatchResult,
    GoalExecutionPolicy,
    GoalToRalphHandoffPromptRequest,
)
from omx_remote.schemas.multi_operator import (
    ManagedOmxFlow,
    ManagedOmxRepo,
    MultiOperatorSnapshot,
)
from omx_remote.schemas.operator import OperatorActionResult, OperatorRecoveryHint
from omx_remote.schemas.ralph import RalphPrdArtifact



def _build_operator_action_result(
    *,
    lane: str,
    action: str,
    loop_state: str,
    next_action: str,
    summary: str,
    recovery_reason: str | None = None,
) -> OperatorActionResult:
    recovery_hint: OperatorRecoveryHint | None
    if recovery_reason is None:
        recovery_hint = None
    else:
        recovery_hint = OperatorRecoveryHint(
            next_action=next_action,
            reason=recovery_reason,
        )

    result = OperatorActionResult(
        lane=lane,
        action=action,
        loop_state=loop_state,
        next_action=next_action,
        summary=summary,
        recovery_hint=recovery_hint,
    )
    return result



def _build_multi_operator_snapshot(
    *,
    include_team_flow: bool = True,
    active_flow_ids: list[str] | None = None,
    include_terminal_team_flow: bool = False,
    ralph_loop_state: str = "success",
    ralph_next_action: str = "observe",
    ralph_summary: str = "ralph is healthy",
    ralph_recovery_reason: str | None = None,
) -> MultiOperatorSnapshot:
    ralph_flow = ManagedOmxFlow(
        flow_id="repo-a:ralph",
        repo_id="repo-a",
        flow_kind="ralph",
        flow_name="ralph",
        last_result=_build_operator_action_result(
            lane="ralph",
            action="launch",
            loop_state=ralph_loop_state,
            next_action=ralph_next_action,
            summary=ralph_summary,
            recovery_reason=ralph_recovery_reason,
        ),
    )

    flows: list[ManagedOmxFlow] = [ralph_flow]

    if include_team_flow:
        team_flow = ManagedOmxFlow(
            flow_id="repo-a:team-alpha",
            repo_id="repo-a",
            flow_kind="team",
            flow_name="team:alpha",
            team_name="alpha",
            last_result=_build_operator_action_result(
                lane="team",
                action="instruction-dispatch",
                loop_state="success",
                next_action="observe",
                summary="team alpha is healthy",
            ),
        )
        flows.append(team_flow)

    if include_terminal_team_flow:
        terminal_team_flow = ManagedOmxFlow(
            flow_id="repo-a:team-beta",
            repo_id="repo-a",
            flow_kind="team",
            flow_name="team:beta",
            team_name="beta",
            last_result=_build_operator_action_result(
                lane="team",
                action="instruction-dispatch",
                loop_state="terminal_failure",
                next_action="escalate",
                summary="team beta failed without a recovery path",
                recovery_reason="terminal failure",
            ),
        )
        flows.append(terminal_team_flow)

    active_flow_ids_value: list[str] = [] if active_flow_ids is None else active_flow_ids
    launchable_flow_ids: list[str] = []
    terminal_flow_ids: list[str] = []
    resumable_flow_ids: list[str] = []
    cleanup_flow_ids: list[str] = []

    if ralph_next_action == "resume":
        resumable_flow_ids.append("repo-a:ralph")
    elif ralph_next_action == "cleanup":
        cleanup_flow_ids.append("repo-a:ralph")

    snapshot = MultiOperatorSnapshot(
        repos=[ManagedOmxRepo(repo_id="repo-a", repo_root="/tmp/repo-a")],
        flows=flows,
        active_flow_ids=active_flow_ids_value,
        launchable_flow_ids=launchable_flow_ids,
        resumable_flow_ids=resumable_flow_ids,
        cleanup_flow_ids=cleanup_flow_ids,
        terminal_flow_ids=terminal_flow_ids,
    )
    return snapshot



def _build_codex_goal_mirror_state() -> CodexGoalMirrorState:
    mirror_state = CodexGoalMirrorState(
        goal_id="goal-1",
        objective_text="Use docs/jobs/schema-type-refactor-hardening as the source of truth.",
        source="codex_goal",
        execution_shape="ralph_pipeline",
        review_policy="review_required",
        team_worker_count=2,
        working_directory="/tmp/repo-a",
        codex_command=["codex", "--enable", "goals"],
        session_locator="agent-remote-goal-goal-1",
        process_id=1234,
        launched_at="2026-05-06T00:00:00Z",
        handoff_state="awaiting_ralph",
        tracking_state="active",
    )
    return mirror_state



def _build_ralph_prd_artifact(
    *,
    objective: str,
    requires_team_fanout: bool = False,
    team_worker_count: int | None = None,
    continuation_policy: str = "continue_automatically",
) -> RalphPrdArtifact:
    result = RalphPrdArtifact(
        objective=objective,
        scope=["stabilize goal to ralph handoff"],
        constraints=["keep ralph independently operable"],
        execution_plan=["reuse typed prd artifacts when still aligned"],
        verification_expectations=["goal delegation reflects typed prd state"],
        requires_team_fanout=requires_team_fanout,
        team_worker_count=team_worker_count,
        continuation_policy=continuation_policy,
    )
    return result



def test_codex_goal_snapshot_rejects_blank_objective_text() -> None:
    capability = CodexGoalCapabilitySnapshot(
        feature_flag_listed=True,
        feature_flag_enabled=False,
        goal_json_surface_verified=False,
        capability_summary="goal feature exists but json surface is unverified",
    )

    with pytest.raises(ValidationError):
        CodexGoalSnapshot(
            goal_id="goal-1",
            objective_text="",
            status="active",
            source="adapter_supervisor",
            capability=capability,
        )



def test_goal_delegation_decision_accepts_ralph_pipeline_target() -> None:
    result = GoalDelegationDecision(
        goal_id="goal-1",
        selected_target="ralph_pipeline",
        reason="the goal now needs structured execution planning",
    )

    assert result.selected_target == "ralph_pipeline"



def test_goal_to_ralph_handoff_prompt_request_requires_source_paths() -> None:
    with pytest.raises(ValidationError):
        GoalToRalphHandoffPromptRequest(
            goal_id="goal-1",
            goal_objective_text="harden schema/type contracts",
            source_paths=(),
            requested_slice="schema config and root base",
            constraints=("keep this refactor-only",),
            verification_expectations=("targeted tests pass",),
            review_policy="review_required",
            team_worker_count=2,
        )



def test_build_goal_to_ralph_handoff_prompt_renders_prd_contract() -> None:
    request = GoalToRalphHandoffPromptRequest(
        goal_id="goal-1",
        goal_objective_text="Use docs/jobs/schema-type-refactor-hardening as the source of truth.",
        source_paths=(
            "docs/jobs/schema-type-refactor-hardening/",
            "AGENTS.md",
            "docs/rules/schema-boundary-rules.md",
        ),
        requested_slice="schema config and root base",
        constraints=(
            "refactor-only hardening",
            "keep Ralph and Team independently operable",
        ),
        verification_expectations=(
            "uv run pytest tests/runtime/test_codex_goal_supervisor.py -q passes",
            "uv run pyrefly check src passes",
        ),
        review_policy="review_required",
        team_worker_count=2,
    )

    prompt = build_goal_to_ralph_handoff_prompt(request)

    assert "You are Ralph" in prompt
    assert "Goal ID: goal-1" in prompt
    assert "Use docs/jobs/schema-type-refactor-hardening" in prompt
    assert "docs/rules/schema-boundary-rules.md" in prompt
    assert "schema config and root base" in prompt
    assert ".omx/prd.json" in prompt
    assert "RalphPrdArtifact" in prompt
    assert "requires_team_fanout" in prompt
    assert "team_worker_count: 2" in prompt
    assert "Do not implement code" in prompt
    assert "Do not launch Team" in prompt
    assert "Stop after creating or validating the PRD artifact" in prompt



def test_prepare_tracked_codex_goal_ralph_handoff_prompt_uses_mirror_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mirror_state = _build_codex_goal_mirror_state()
    monkeypatch.setattr(
        codex_goal_supervisor,
        "read_codex_goal_status",
        lambda working_directory: mirror_state,
    )

    result = prepare_tracked_codex_goal_ralph_handoff_prompt(
        working_directory="/tmp/repo-a",
        source_paths=("docs/jobs/schema-type-refactor-hardening/", "AGENTS.md"),
        requested_slice="schema config and root base",
        constraints=("refactor-only hardening",),
        verification_expectations=("targeted tests pass",),
    )

    assert result.mirror_state.goal_id == "goal-1"
    assert result.prompt_request.goal_id == "goal-1"
    assert result.prompt_request.goal_objective_text == mirror_state.objective_text
    assert result.prompt_request.review_policy == "review_required"
    assert result.prompt_request.team_worker_count == 2
    assert "schema config and root base" in result.prompt
    assert "Stop after creating or validating the PRD artifact" in result.prompt



def test_goal_delegation_decision_requires_team_worker_count_for_team_fanout() -> None:
    with pytest.raises(ValidationError):
        GoalDelegationDecision(
            goal_id="goal-1",
            selected_target="ralph_pipeline",
            reason="the goal needs typed team fanout",
            requires_team_fanout=True,
        )



def test_goal_execution_policy_defaults_allow_goal_standalone_and_ralph_pipeline() -> None:
    result = GoalExecutionPolicy()

    assert result.allow_goal_standalone is True
    assert result.allow_ralph_pipeline is True
    assert result.prds_require_review_before_execution is False



def test_build_codex_goal_snapshot_collects_tracked_active_and_blocked_flow_state() -> None:
    snapshot = _build_multi_operator_snapshot(
        active_flow_ids=["repo-a:ralph"],
        include_terminal_team_flow=True,
    )
    capability = CodexGoalCapabilitySnapshot(
        feature_flag_listed=True,
        feature_flag_enabled=False,
        goal_json_surface_verified=False,
        capability_summary="goal feature exists but json surface is unverified",
    )

    result = build_codex_goal_snapshot(
        goal_id="goal-1",
        objective_text="ship the typed goal supervisor slice",
        capability=capability,
        multi_operator_snapshot=snapshot,
    )

    assert result.tracked_flow_ids == [
        "repo-a:ralph",
        "repo-a:team-alpha",
        "repo-a:team-beta",
    ]
    assert result.active_flow_ids == ["repo-a:ralph"]
    assert result.open_blockers == [
        "repo-a:team-beta: team beta failed without a recovery path"
    ]



def test_select_goal_delegation_returns_observe_only_for_active_tracked_flow() -> None:
    snapshot = _build_multi_operator_snapshot(active_flow_ids=["repo-a:ralph"])

    result = select_goal_delegation(
        goal_id="goal-1",
        multi_operator_snapshot=snapshot,
        execution_policy=GoalExecutionPolicy(),
        objective_is_already_structured=False,
        requires_parallel_fanout=False,
        goal_should_remain_standalone=False,
    )

    assert result.selected_target == "observe_only"



def test_select_goal_delegation_returns_goal_only_when_goal_should_remain_standalone() -> None:
    snapshot = _build_multi_operator_snapshot()

    result = select_goal_delegation(
        goal_id="goal-1",
        multi_operator_snapshot=snapshot,
        execution_policy=GoalExecutionPolicy(),
        objective_is_already_structured=False,
        requires_parallel_fanout=False,
        goal_should_remain_standalone=True,
    )

    assert result.selected_target == "goal_only"



def test_select_goal_delegation_returns_ralph_pipeline_with_team_fanout() -> None:
    snapshot = _build_multi_operator_snapshot(include_team_flow=True)

    result = select_goal_delegation(
        goal_id="goal-1",
        multi_operator_snapshot=snapshot,
        execution_policy=GoalExecutionPolicy(),
        objective_is_already_structured=False,
        requires_parallel_fanout=True,
        requested_team_worker_count=3,
        goal_should_remain_standalone=False,
    )

    assert result.selected_target == "ralph_pipeline"
    assert result.requires_prd_refresh is True
    assert result.requires_team_fanout is True
    assert result.team_worker_count == 3
    assert result.can_finish_without_team is False



def test_select_goal_delegation_returns_ralph_pipeline_when_team_is_unnecessary() -> None:
    snapshot = _build_multi_operator_snapshot(include_team_flow=False)

    result = select_goal_delegation(
        goal_id="goal-1",
        multi_operator_snapshot=snapshot,
        execution_policy=GoalExecutionPolicy(),
        objective_is_already_structured=False,
        requires_parallel_fanout=False,
        goal_should_remain_standalone=False,
    )

    assert result.selected_target == "ralph_pipeline"
    assert result.requires_team_fanout is False
    assert result.can_finish_without_team is True



def test_select_goal_delegation_reflects_prd_review_policy() -> None:
    snapshot = _build_multi_operator_snapshot()
    execution_policy = GoalExecutionPolicy(prds_require_review_before_execution=True)

    result = select_goal_delegation(
        goal_id="goal-1",
        multi_operator_snapshot=snapshot,
        execution_policy=execution_policy,
        objective_is_already_structured=False,
        requires_parallel_fanout=True,
        requested_team_worker_count=2,
        goal_should_remain_standalone=False,
    )

    assert result.selected_target == "ralph_pipeline"
    assert result.requires_prd_review is True



def test_select_goal_delegation_requires_prd_refresh_when_no_prd_artifact_exists() -> None:
    snapshot = _build_multi_operator_snapshot(include_team_flow=False)

    result = select_goal_delegation(
        goal_id="goal-1",
        multi_operator_snapshot=snapshot,
        execution_policy=GoalExecutionPolicy(),
        objective_is_already_structured=True,
        requires_parallel_fanout=False,
        goal_should_remain_standalone=False,
        goal_objective_text="Ship the typed goal to Ralph bridge",
        ralph_prd_artifact=None,
    )

    assert result.selected_target == "ralph_pipeline"
    assert result.requires_prd_refresh is True



def test_select_goal_delegation_reuses_matching_prd_artifact() -> None:
    snapshot = _build_multi_operator_snapshot(include_team_flow=False)
    prd_artifact = _build_ralph_prd_artifact(
        objective="  ship the typed goal to ralph bridge  ",
    )

    result = select_goal_delegation(
        goal_id="goal-1",
        multi_operator_snapshot=snapshot,
        execution_policy=GoalExecutionPolicy(),
        objective_is_already_structured=False,
        requires_parallel_fanout=False,
        goal_should_remain_standalone=False,
        goal_objective_text="Ship The Typed Goal To Ralph Bridge",
        ralph_prd_artifact=prd_artifact,
    )

    assert result.selected_target == "ralph_pipeline"
    assert result.requires_prd_refresh is False
    assert result.can_finish_without_team is True



def test_select_goal_delegation_refreshes_mismatched_prd_artifact() -> None:
    snapshot = _build_multi_operator_snapshot(include_team_flow=False)
    prd_artifact = _build_ralph_prd_artifact(
        objective="Ship a different objective entirely",
    )

    result = select_goal_delegation(
        goal_id="goal-1",
        multi_operator_snapshot=snapshot,
        execution_policy=GoalExecutionPolicy(),
        objective_is_already_structured=True,
        requires_parallel_fanout=False,
        goal_should_remain_standalone=False,
        goal_objective_text="Ship the typed goal to Ralph bridge",
        ralph_prd_artifact=prd_artifact,
    )

    assert result.selected_target == "ralph_pipeline"
    assert result.requires_prd_refresh is True



def test_select_goal_delegation_reads_review_policy_from_matching_prd_artifact() -> None:
    snapshot = _build_multi_operator_snapshot(include_team_flow=False)
    prd_artifact = _build_ralph_prd_artifact(
        objective="Ship the typed goal to Ralph bridge",
        continuation_policy="review_required",
    )

    result = select_goal_delegation(
        goal_id="goal-1",
        multi_operator_snapshot=snapshot,
        execution_policy=GoalExecutionPolicy(),
        objective_is_already_structured=False,
        requires_parallel_fanout=False,
        goal_should_remain_standalone=False,
        goal_objective_text="Ship the typed goal to Ralph bridge",
        ralph_prd_artifact=prd_artifact,
    )

    assert result.selected_target == "ralph_pipeline"
    assert result.requires_prd_review is True



def test_select_goal_delegation_reads_team_fanout_from_matching_prd_artifact() -> None:
    snapshot = _build_multi_operator_snapshot(include_team_flow=True)
    prd_artifact = _build_ralph_prd_artifact(
        objective="Ship the typed goal to Ralph bridge",
        requires_team_fanout=True,
        team_worker_count=5,
    )

    result = select_goal_delegation(
        goal_id="goal-1",
        multi_operator_snapshot=snapshot,
        execution_policy=GoalExecutionPolicy(),
        objective_is_already_structured=False,
        requires_parallel_fanout=False,
        goal_should_remain_standalone=False,
        goal_objective_text="Ship the typed goal to Ralph bridge",
        ralph_prd_artifact=prd_artifact,
    )

    assert result.selected_target == "ralph_pipeline"
    assert result.requires_prd_refresh is False
    assert result.requires_team_fanout is True
    assert result.team_worker_count == 5
    assert result.can_finish_without_team is False



def test_goal_delegation_dispatch_result_defaults_to_none_action() -> None:
    result = GoalDelegationDispatchResult(
        goal_id="goal-1",
        selected_target="goal_only",
        dispatch_status="not_applicable",
    )

    assert result.dispatched_action == "none"
    assert result.operator_result is None



def test_dispatch_goal_delegation_returns_not_applicable_for_goal_only() -> None:
    snapshot = _build_multi_operator_snapshot()
    decision = GoalDelegationDecision(
        goal_id="goal-1",
        selected_target="goal_only",
        reason="keep tracking the goal without delegating",
    )

    result = dispatch_goal_delegation(
        decision=decision,
        multi_operator_snapshot=snapshot,
        goal_objective_text="Ship the typed goal to Ralph bridge",
        force_cleanup=False,
        allow_non_tty=True,
    )

    assert result.dispatch_status == "not_applicable"
    assert result.dispatched_action == "none"
    assert result.operator_result is None



def test_dispatch_goal_delegation_blocks_when_prd_refresh_is_required() -> None:
    snapshot = _build_multi_operator_snapshot()
    decision = GoalDelegationDecision(
        goal_id="goal-1",
        selected_target="ralph_pipeline",
        reason="Ralph must refresh the PRD first",
        requires_prd_refresh=True,
    )

    result = dispatch_goal_delegation(
        decision=decision,
        multi_operator_snapshot=snapshot,
        goal_objective_text="Ship the typed goal to Ralph bridge",
        force_cleanup=False,
        allow_non_tty=True,
    )

    assert result.dispatch_status == "blocked"
    assert result.dispatched_action == "none"
    assert result.blocker_reason == "the goal still requires Ralph PRD refresh before dispatch"



def test_dispatch_goal_delegation_blocks_when_prd_review_is_required() -> None:
    snapshot = _build_multi_operator_snapshot()
    decision = GoalDelegationDecision(
        goal_id="goal-1",
        selected_target="ralph_pipeline",
        reason="Ralph PRD needs review before execution",
        requires_prd_review=True,
    )

    result = dispatch_goal_delegation(
        decision=decision,
        multi_operator_snapshot=snapshot,
        goal_objective_text="Ship the typed goal to Ralph bridge",
        force_cleanup=False,
        allow_non_tty=True,
    )

    assert result.dispatch_status == "blocked"
    assert result.dispatched_action == "none"
    assert result.blocker_reason == "the goal still requires Ralph PRD review before dispatch"



def test_dispatch_goal_delegation_blocks_when_ralph_cleanup_is_required() -> None:
    snapshot = _build_multi_operator_snapshot(
        include_team_flow=False,
        ralph_loop_state="stale_state_failure",
        ralph_next_action="cleanup",
        ralph_summary="Ralph has stale state and must be cleaned first",
        ralph_recovery_reason="cleanup first",
    )
    decision = GoalDelegationDecision(
        goal_id="goal-1",
        selected_target="ralph_pipeline",
        reason="Ralph pipeline is selected",
    )

    result = dispatch_goal_delegation(
        decision=decision,
        multi_operator_snapshot=snapshot,
        goal_objective_text="Ship the typed goal to Ralph bridge",
        force_cleanup=False,
        allow_non_tty=True,
    )

    assert result.dispatch_status == "blocked"
    assert result.dispatched_action == "none"
    assert result.blocker_reason == "the tracked Ralph flow requires cleanup before Goal can dispatch it"



def test_dispatch_goal_delegation_resumes_ralph_when_resumable_flow_exists(monkeypatch) -> None:
    snapshot = _build_multi_operator_snapshot(
        include_team_flow=False,
        ralph_loop_state="resumable_later",
        ralph_next_action="resume",
        ralph_summary="Ralph can resume from the existing state",
    )

    def fake_operate_ralph_resume() -> OperatorActionResult:
        result = _build_operator_action_result(
            lane="ralph",
            action="resume",
            loop_state="success",
            next_action="observe",
            summary="ralph resumed successfully",
        )
        return result

    monkeypatch.setattr(
        "omx_remote.runtime.codex_goal_supervisor.operate_ralph_resume",
        fake_operate_ralph_resume,
    )

    decision = GoalDelegationDecision(
        goal_id="goal-1",
        selected_target="ralph_pipeline",
        reason="resume the existing Ralph flow",
    )

    result = dispatch_goal_delegation(
        decision=decision,
        multi_operator_snapshot=snapshot,
        goal_objective_text="Ship the typed goal to Ralph bridge",
        force_cleanup=False,
        allow_non_tty=True,
    )

    assert result.dispatch_status == "dispatched"
    assert result.dispatched_action == "ralph_resume"
    assert result.operator_result is not None
    assert result.operator_result.action == "resume"



def test_dispatch_goal_delegation_launches_team_when_pipeline_requires_fanout(
    monkeypatch,
) -> None:
    snapshot = _build_multi_operator_snapshot(include_team_flow=True)

    def fake_operate_ralph_team_launch(*, allow_non_tty: bool) -> OperatorActionResult:
        _ = allow_non_tty
        result = _build_operator_action_result(
            lane="team",
            action="launch",
            loop_state="success",
            next_action="observe",
            summary="team launched from the matching Ralph PRD artifact",
        )
        return result

    monkeypatch.setattr(
        "omx_remote.runtime.codex_goal_supervisor.operate_ralph_team_launch",
        fake_operate_ralph_team_launch,
    )

    decision = GoalDelegationDecision(
        goal_id="goal-1",
        selected_target="ralph_pipeline",
        reason="launch Team from the existing Ralph PRD artifact",
        requires_team_fanout=True,
        team_worker_count=3,
    )

    result = dispatch_goal_delegation(
        decision=decision,
        multi_operator_snapshot=snapshot,
        goal_objective_text="Ship the typed goal to Ralph bridge",
        force_cleanup=False,
        allow_non_tty=True,
    )

    assert result.dispatch_status == "dispatched"
    assert result.dispatched_action == "team_launch"
    assert result.operator_result is not None
    assert result.operator_result.lane == "team"
    assert result.operator_result.action == "launch"



def test_dispatch_goal_delegation_launches_ralph_when_pipeline_is_executable(
    monkeypatch,
) -> None:
    snapshot = _build_multi_operator_snapshot(include_team_flow=False)

    def fake_operate_ralph_launch(
        task: str,
        *,
        force_cleanup: bool,
        allow_non_tty: bool,
    ) -> OperatorActionResult:
        _ = (force_cleanup, allow_non_tty)
        result = _build_operator_action_result(
            lane="ralph",
            action="launch",
            loop_state="success",
            next_action="observe",
            summary=f"ralph launched for {task}",
        )
        return result

    monkeypatch.setattr(
        "omx_remote.runtime.codex_goal_supervisor.operate_ralph_launch",
        fake_operate_ralph_launch,
    )

    decision = GoalDelegationDecision(
        goal_id="goal-1",
        selected_target="ralph_pipeline",
        reason="launch Ralph for the goal",
    )

    result = dispatch_goal_delegation(
        decision=decision,
        multi_operator_snapshot=snapshot,
        goal_objective_text="Ship the typed goal to Ralph bridge",
        force_cleanup=False,
        allow_non_tty=True,
    )

    assert result.dispatch_status == "dispatched"
    assert result.dispatched_action == "ralph_launch"
    assert result.operator_result is not None
    assert result.operator_result.action == "launch"
    assert result.operator_result.summary == "ralph launched for Ship the typed goal to Ralph bridge"



def test_dispatch_goal_delegation_marks_goal_handoff_started_when_ralph_launches(
    monkeypatch,
    tmp_path: Path,
) -> None:
    snapshot = _build_multi_operator_snapshot(include_team_flow=False)
    state_dir = tmp_path / ".agent-remote" / "state"
    state_dir.mkdir(parents=True)
    state_path = state_dir / "codex-goal.json"
    state_path.write_text(
        json.dumps(
            {
                "goal_id": "goal-1",
                "objective_text": "Ship the typed goal to Ralph bridge",
                "source": "codex_goal",
                "execution_shape": "ralph_pipeline",
                "review_policy": "continue_automatically",
                "team_worker_count": None,
                "working_directory": str(tmp_path),
                "codex_command": ["codex", "--enable", "goals"],
                "session_locator": "agent-remote-goal-goal-1",
                "process_id": 1234,
                "launched_at": "2026-05-05T12:00:00+00:00",
                "handoff_state": "awaiting_ralph",
                "tracking_state": "active"
            }
        ),
        encoding="utf-8",
    )

    def fake_operate_ralph_launch(
        task: str,
        *,
        force_cleanup: bool,
        allow_non_tty: bool,
    ) -> OperatorActionResult:
        _ = (task, force_cleanup, allow_non_tty)
        result = _build_operator_action_result(
            lane="ralph",
            action="launch",
            loop_state="success",
            next_action="observe",
            summary="ralph launched successfully",
        )
        return result

    monkeypatch.setattr(
        "omx_remote.runtime.codex_goal_supervisor.operate_ralph_launch",
        fake_operate_ralph_launch,
    )

    decision = GoalDelegationDecision(
        goal_id="goal-1",
        selected_target="ralph_pipeline",
        reason="launch Ralph for the goal",
    )

    result = dispatch_goal_delegation(
        decision=decision,
        multi_operator_snapshot=snapshot,
        goal_objective_text="Ship the typed goal to Ralph bridge",
        goal_working_directory=str(tmp_path),
        force_cleanup=False,
        allow_non_tty=True,
    )
    persisted_payload = json.loads(state_path.read_text(encoding="utf-8"))

    assert result.dispatch_status == "dispatched"
    assert result.dispatched_action == "ralph_launch"
    assert persisted_payload["handoff_state"] == "ralph_started"



def test_advance_tracked_codex_goal_returns_goal_only_when_mirror_state_is_goal_only(
    monkeypatch,
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / ".agent-remote" / "state"
    state_dir.mkdir(parents=True)
    state_path = state_dir / "codex-goal.json"
    state_path.write_text(
        json.dumps(
            {
                "goal_id": "goal-1",
                "objective_text": "Keep native goal standalone",
                "source": "codex_goal",
                "execution_shape": "goal_only",
                "review_policy": "continue_automatically",
                "team_worker_count": None,
                "working_directory": str(tmp_path),
                "codex_command": ["codex", "--enable", "goals"],
                "session_locator": "agent-remote-goal-goal-1",
                "process_id": 1234,
                "launched_at": "2026-05-05T12:00:00+00:00",
                "handoff_state": "goal_only",
                "tracking_state": "starting"
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "omx_remote.runtime.codex_goal_runtime.is_codex_goal_session_active",
        lambda session_locator: True,
    )

    request = CodexGoalAdvanceRequest(
        capability=CodexGoalCapabilitySnapshot(
            feature_flag_listed=True,
            feature_flag_enabled=True,
            goal_json_surface_verified=False,
            capability_summary="native goal is available but still adapter-tracked",
        ),
        multi_operator_snapshot=_build_multi_operator_snapshot(),
        objective_is_already_structured=False,
        allow_non_tty=True,
    )

    result = advance_tracked_codex_goal(
        request=request,
        working_directory=str(tmp_path),
    )

    assert result.mirror_state.goal_id == "goal-1"
    assert result.goal_snapshot.objective_text == "Keep native goal standalone"
    assert result.decision.selected_target == "goal_only"
    assert result.dispatch_result.dispatch_status == "not_applicable"



def test_advance_tracked_codex_goal_promotes_review_required_from_mirror_state(
    monkeypatch,
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / ".agent-remote" / "state"
    state_dir.mkdir(parents=True)
    state_path = state_dir / "codex-goal.json"
    state_path.write_text(
        json.dumps(
            {
                "goal_id": "goal-1",
                "objective_text": "Require review before Ralph dispatch",
                "source": "codex_goal",
                "execution_shape": "ralph_pipeline",
                "review_policy": "review_required",
                "team_worker_count": None,
                "working_directory": str(tmp_path),
                "codex_command": ["codex", "--enable", "goals"],
                "session_locator": "agent-remote-goal-goal-1",
                "process_id": 1234,
                "launched_at": "2026-05-05T12:00:00+00:00",
                "handoff_state": "awaiting_ralph",
                "tracking_state": "starting"
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "omx_remote.runtime.codex_goal_runtime.is_codex_goal_session_active",
        lambda session_locator: True,
    )

    request = CodexGoalAdvanceRequest(
        capability=CodexGoalCapabilitySnapshot(
            feature_flag_listed=True,
            feature_flag_enabled=True,
            goal_json_surface_verified=False,
            capability_summary="native goal is available but still adapter-tracked",
        ),
        multi_operator_snapshot=_build_multi_operator_snapshot(include_team_flow=False),
        objective_is_already_structured=True,
        ralph_prd_artifact=_build_ralph_prd_artifact(
            objective="Require review before Ralph dispatch",
            continuation_policy="continue_automatically",
        ),
        allow_non_tty=True,
    )

    result = advance_tracked_codex_goal(
        request=request,
        working_directory=str(tmp_path),
    )

    assert result.execution_policy.prds_require_review_before_execution is True
    assert result.decision.requires_prd_review is True
    assert result.dispatch_result.dispatch_status == "blocked"



def test_advance_tracked_codex_goal_dispatches_team_from_mirror_state(
    monkeypatch,
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / ".agent-remote" / "state"
    state_dir.mkdir(parents=True)
    state_path = state_dir / "codex-goal.json"
    state_path.write_text(
        json.dumps(
            {
                "goal_id": "goal-1",
                "objective_text": "Fan out native goal through Ralph",
                "source": "codex_goal",
                "execution_shape": "ralph_pipeline",
                "review_policy": "continue_automatically",
                "team_worker_count": 3,
                "working_directory": str(tmp_path),
                "codex_command": ["codex", "--enable", "goals"],
                "session_locator": "agent-remote-goal-goal-1",
                "process_id": 1234,
                "launched_at": "2026-05-05T12:00:00+00:00",
                "handoff_state": "awaiting_ralph",
                "tracking_state": "starting"
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "omx_remote.runtime.codex_goal_runtime.is_codex_goal_session_active",
        lambda session_locator: True,
    )

    def fake_operate_ralph_team_launch(*, allow_non_tty: bool) -> OperatorActionResult:
        _ = allow_non_tty
        result = _build_operator_action_result(
            lane="team",
            action="launch",
            loop_state="success",
            next_action="observe",
            summary="team launched from tracked native goal state",
        )
        return result

    monkeypatch.setattr(
        "omx_remote.runtime.codex_goal_supervisor.operate_ralph_team_launch",
        fake_operate_ralph_team_launch,
    )

    request = CodexGoalAdvanceRequest(
        capability=CodexGoalCapabilitySnapshot(
            feature_flag_listed=True,
            feature_flag_enabled=True,
            goal_json_surface_verified=False,
            capability_summary="native goal is available but still adapter-tracked",
        ),
        multi_operator_snapshot=_build_multi_operator_snapshot(include_team_flow=True),
        objective_is_already_structured=True,
        ralph_prd_artifact=_build_ralph_prd_artifact(
            objective="Fan out native goal through Ralph",
            requires_team_fanout=True,
            team_worker_count=3,
        ),
        allow_non_tty=True,
    )

    result = advance_tracked_codex_goal(
        request=request,
        working_directory=str(tmp_path),
    )
    persisted_payload = json.loads(state_path.read_text(encoding="utf-8"))

    assert result.decision.requires_team_fanout is True
    assert result.decision.team_worker_count == 3
    assert result.dispatch_result.dispatched_action == "team_launch"
    assert persisted_payload["handoff_state"] == "ralph_started"
