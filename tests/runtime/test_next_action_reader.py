from pathlib import Path
from shlex import quote as quote_shell_token

from omx_remote.runtime.next.next_action_reader import build_next_action_result
from omx_remote.runtime.routes.route_policy_engine import build_route_policy_result
from omx_remote.schemas.cockpit.capability_snapshot_schemas import (
    CockpitAgentConfigSummary,
    CockpitCapabilitiesSnapshot,
    CockpitCapabilityCommand,
    CockpitCommandRecipeSummary,
    CockpitRuntimeCapability,
)
from omx_remote.schemas.cockpit.snapshot_schemas import (
    CockpitContradiction,
    CockpitDecisionReason,
    CockpitSnapshot,
)
from omx_remote.schemas.route_policy_schemas import RouteName


def _capabilities() -> CockpitCapabilitiesSnapshot:
    return CockpitCapabilitiesSnapshot(
        codex=CockpitRuntimeCapability(
            name="codex",
            available=True,
            executable_path="/usr/bin/codex",
            version="codex 0.133.0",
            commands=(
                CockpitCapabilityCommand(
                    name="exec_json",
                    available=True,
                    detail="codex exec --json is available.",
                ),
            ),
        ),
        omx=CockpitRuntimeCapability(
            name="omx",
            available=True,
            executable_path="/usr/bin/omx",
            version="omx 0.18.0",
            commands=(
                CockpitCapabilityCommand(
                    name="ultragoal",
                    available=True,
                    detail="omx ultragoal --help succeeded.",
                ),
                CockpitCapabilityCommand(
                    name="team",
                    available=True,
                    detail="omx team --help succeeded.",
                ),
            ),
        ),
    )


def _agents() -> CockpitAgentConfigSummary:
    return CockpitAgentConfigSummary(
        config_path=".comx-agent.toml",
        total_count=1,
        enabled_count=1,
        disabled_count=0,
        enabled_agent_ids=("implementer",),
        warnings=(),
    )


def _recipes() -> CockpitCommandRecipeSummary:
    return CockpitCommandRecipeSummary(
        available_count=2,
        builtin_count=2,
        repo_count=0,
        qualified_ids=("builtin:review-gate", "builtin:release-readiness"),
        warnings=(),
    )


def _cockpit(
    tmp_path: Path,
    *,
    safe_to_mutate: bool = True,
    recommended_next_action: str = "observe",
    contradictions: tuple[CockpitContradiction, ...] = (),
    decision_reasons: tuple[CockpitDecisionReason, ...] = (),
) -> CockpitSnapshot:
    if not decision_reasons:
        decision_reasons = (
            CockpitDecisionReason(
                category="no_blocking_evidence",
                detail="No active runtime evidence was found.",
                recommended_next_action=recommended_next_action,
                blocks_mutation=False,
                source_names=("runtime_status", "active_runtime_modes"),
            ),
        )
    snapshot = CockpitSnapshot(
        repo_root=str(tmp_path),
        runtime_summary="No active modes.",
        active_runtime_modes=(),
        capabilities=_capabilities(),
        configured_agents=_agents(),
        command_recipes=_recipes(),
        contradictions=contradictions,
        lanes=(),
        safe_to_mutate=safe_to_mutate,
        recommended_next_action=recommended_next_action,
        decision_reasons=decision_reasons,
    )
    return snapshot


def test_next_action_observes_when_repo_has_no_blocking_evidence(
    tmp_path: Path,
) -> None:
    result = build_next_action_result(cockpit_snapshot=_cockpit(tmp_path))

    assert result.recommended_action == "observe"
    assert result.safe_to_mutate is True
    assert result.requires_review is False
    assert result.source_names == ("runtime_status", "active_runtime_modes")
    assert result.recommended_commands == (
        f"comx-agent cockpit snapshot --cwd {quote_shell_token(str(tmp_path))} --json",
    )


def test_next_action_inspects_team_evidence_before_mutation(tmp_path: Path) -> None:
    team_reason = CockpitDecisionReason(
        category="active_team_evidence",
        detail="Active Team evidence is present for: alpha-team.",
        recommended_next_action="inspect_team_evidence",
        blocks_mutation=True,
        source_names=("team_evidence", "team_proof_layer:worker_readiness"),
    )
    result = build_next_action_result(
        cockpit_snapshot=_cockpit(
            tmp_path,
            safe_to_mutate=False,
            recommended_next_action="inspect_team_evidence",
            decision_reasons=(team_reason,),
        )
    )

    assert result.recommended_action == "inspect_team_evidence"
    assert result.safe_to_mutate is False
    assert result.requires_review is True
    assert result.source_names == ("team_evidence", "team_proof_layer:worker_readiness")
    assert "mutating runtime launch/cleanup commands" in result.blocked_actions


def test_next_action_prioritizes_cockpit_contradictions(tmp_path: Path) -> None:
    contradiction = CockpitContradiction(
        category="runtime_activity_conflict",
        message="Runtime surfaces disagree.",
    )
    contradiction_reason = CockpitDecisionReason(
        category="runtime_contradiction",
        detail="Runtime surfaces disagree.",
        recommended_next_action="inspect_runtime_contradiction",
        blocks_mutation=True,
        source_names=("runtime_status", "active_runtime_modes"),
    )
    route_policy = build_route_policy_result(
        task="execute this durable roadmap",
        cwd=tmp_path,
        capabilities=_capabilities(),
        agent_summary=_agents(),
        recipe_summary=_recipes(),
    )
    result = build_next_action_result(
        cockpit_snapshot=_cockpit(
            tmp_path,
            safe_to_mutate=False,
            recommended_next_action="inspect_runtime_contradiction",
            contradictions=(contradiction,),
            decision_reasons=(contradiction_reason,),
        ),
        task="execute this durable roadmap",
        route_policy=route_policy,
    )

    assert result.recommended_action == "inspect_runtime_contradiction"
    assert result.requires_review is True
    assert result.route_recommendations[0].route == RouteName.OMX_ULTRAGOAL


def test_next_action_includes_ultragoal_route_for_durable_task(tmp_path: Path) -> None:
    task = "plan a durable multi-slice runtime hardening roadmap"
    route_policy = build_route_policy_result(
        task=task,
        cwd=tmp_path,
        capabilities=_capabilities(),
        agent_summary=_agents(),
        recipe_summary=_recipes(),
        safe_to_mutate=True,
        active_runtime_modes=(),
    )

    result = build_next_action_result(
        cockpit_snapshot=_cockpit(tmp_path),
        task=task,
        route_policy=route_policy,
    )

    assert result.recommended_action == "prepare_ultragoal_handoff"
    assert result.route_recommendations[0].route == RouteName.OMX_ULTRAGOAL
    assert result.recommended_commands == (
        f"comx-agent cockpit snapshot --cwd {quote_shell_token(str(tmp_path))} --json",
        (
            "comx-agent route recommend "
            f"--cwd {quote_shell_token(str(tmp_path))} "
            f"--task {quote_shell_token(task)} --json"
        ),
        f"comx-agent ultragoal status --cwd {quote_shell_token(str(tmp_path))} --json",
        (
            "comx-agent preflight route omx-ultragoal "
            f"--cwd {quote_shell_token(str(tmp_path))} --json"
        ),
    )


def test_next_action_keeps_verification_recommendations_dry_run_first(
    tmp_path: Path,
) -> None:
    task = "verify current handoff"
    route_policy = build_route_policy_result(
        task=task,
        cwd=tmp_path,
        capabilities=_capabilities(),
        agent_summary=_agents(),
        recipe_summary=_recipes(),
        safe_to_mutate=True,
        active_runtime_modes=(),
    )

    result = build_next_action_result(
        cockpit_snapshot=_cockpit(tmp_path),
        task=task,
        route_policy=route_policy,
    )

    assert result.recommended_action == "inspect_route_recommendation"
    assert all(
        "omx team launch" not in command for command in result.recommended_commands
    )
    assert any("--dry-run" in command for command in result.recommended_commands)
