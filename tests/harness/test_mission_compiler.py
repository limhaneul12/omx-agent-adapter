from pathlib import Path

import pytest
from comx_harness.application.mission_compiler import MissionCompiler
from comx_harness.schemas.execution_schemas import RunOptions
from comx_harness.schemas.mission_schemas import (
    MissionConstraints,
    MissionRequest,
)
from comx_harness.shared.harness_enums.execution_enums import SandboxMode
from comx_harness.shared.harness_enums.mission_enums import MissionExecutionProfile
from comx_harness.shared.harness_enums.provider_enums import ProviderId
from comx_harness.shared.harness_enums.strategy_enums import (
    StrategyNodeType,
    StrategyRunCondition,
    StrategyValidatorKind,
)
from pydantic import ValidationError


def _request(
    workspace: Path,
    profile: MissionExecutionProfile,
    *,
    mutation_allowed: bool = False,
) -> MissionRequest:
    options = RunOptions(
        sandbox=(
            SandboxMode.WORKSPACE_WRITE if mutation_allowed else SandboxMode.READ_ONLY
        )
    )
    return MissionRequest(
        mission_id=f"mission-{profile}",
        controller_id="test-controller",
        objective="Inspect and improve the target without unrelated changes.",
        workspace=str(workspace.resolve()),
        execution_profile=profile,
        constraints=MissionConstraints(mutation_allowed=mutation_allowed),
        options=options,
    )


@pytest.mark.parametrize(
    ("profile", "provider"),
    (
        (MissionExecutionProfile.CODEX_NATIVE, ProviderId.CODEX),
        (MissionExecutionProfile.OMX_NATIVE, ProviderId.OMX),
    ),
)
def test_direct_profiles_compile_to_one_native_run_and_finish(
    tmp_path: Path,
    profile: MissionExecutionProfile,
    provider: ProviderId,
) -> None:
    request = _request(tmp_path, profile)

    plan = MissionCompiler().compile(request)

    assert plan.request == request
    assert tuple(stage.node_type for stage in plan.strategy.stages) == (
        StrategyNodeType.NATIVE_RUN,
        StrategyNodeType.FINISH,
    )
    assert plan.strategy.stages[0].provider == provider
    assert plan.strategy.stages[0].mutation_allowed is False
    assert "Do not modify the workspace" in plan.strategy.stages[0].objective
    assert plan.strategy.stages[-1].dependencies == ("primary-run",)


def test_review_profile_compiles_verified_conditional_resume(tmp_path: Path) -> None:
    request = _request(
        tmp_path,
        MissionExecutionProfile.CODEX_THEN_OMX_REVIEW,
        mutation_allowed=True,
    )

    plan = MissionCompiler().compile(request)
    stages = plan.strategy.stages

    assert tuple(stage.stage_id for stage in stages) == (
        "codex-primary",
        "omx-review",
        "blocker-gate",
        "codex-resume",
        "finish",
    )
    assert stages[0].provider == ProviderId.CODEX
    assert stages[1].provider == ProviderId.OMX
    assert stages[1].node_type == StrategyNodeType.HANDOFF
    assert stages[1].input_artifacts == ("result",)
    assert stages[2].validator_kind == StrategyValidatorKind.BLOCKER_COUNT
    assert stages[2].completion_criteria.max_blockers == 0
    assert stages[3].node_type == StrategyNodeType.NATIVE_RESUME
    assert stages[3].source_stage_id == "codex-primary"
    assert stages[3].run_condition == StrategyRunCondition.ANY_DEPENDENCY_FAILED
    assert stages[4].run_condition == StrategyRunCondition.ANY_DEPENDENCY_SUCCEEDED
    blocker_path = stages[2].input_artifacts[0]
    assert blocker_path.endswith(
        ".comx-agent/v2/mission-artifacts/mission-codex-then-omx-review/blockers.json"
    )
    assert blocker_path in stages[1].expected_artifacts
    assert "No automatic model or Harness router was used." in plan.decisions


def test_mission_compilation_is_deterministic(tmp_path: Path) -> None:
    request = _request(tmp_path, MissionExecutionProfile.CODEX_NATIVE)
    compiler = MissionCompiler()

    first = compiler.compile(request)
    second = compiler.compile(request)

    assert first == second


def test_mission_rejects_implicit_writable_sandbox(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="mutation_allowed=false"):
        MissionRequest(
            mission_id="unsafe-write",
            objective="Reject an implicit write boundary.",
            workspace=str(tmp_path),
            execution_profile=MissionExecutionProfile.CODEX_NATIVE,
            options=RunOptions(sandbox=SandboxMode.WORKSPACE_WRITE),
        )


def test_mission_rejects_mutation_without_explicit_writable_sandbox(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValidationError, match="explicit writable sandbox"):
        MissionRequest(
            mission_id="missing-write-boundary",
            objective="Reject ambiguous mutation permissions.",
            workspace=str(tmp_path),
            execution_profile=MissionExecutionProfile.CODEX_NATIVE,
            constraints=MissionConstraints(mutation_allowed=True),
        )


def test_review_profile_rejects_read_only_contract(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="review requires mutation_allowed=true"):
        MissionRequest(
            mission_id="readonly-review",
            objective="Review without a writable blocker artifact boundary.",
            workspace=str(tmp_path),
            execution_profile=MissionExecutionProfile.CODEX_THEN_OMX_REVIEW,
        )


def test_mission_rejects_arbitrary_shell_and_auto_profile(tmp_path: Path) -> None:
    base = {
        "mission_id": "strict-boundary",
        "objective": "Reject undeclared execution surfaces.",
        "workspace": str(tmp_path),
        "execution_profile": "codex-native",
    }
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        MissionRequest.model_validate({**base, "shell": "rm -rf ."})
    with pytest.raises(ValidationError, match="Input should be"):
        MissionRequest.model_validate({**base, "execution_profile": "auto"})
