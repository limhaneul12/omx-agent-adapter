from __future__ import annotations

from pathlib import Path

from comx_harness.schemas.mission_schemas import MissionPlan, MissionRequest
from comx_harness.schemas.strategy_schemas import (
    StrategyCompletionCriteria,
    StrategyDefinition,
    StrategyFailurePolicy,
    StrategyStage,
)
from comx_harness.shared.harness_enums.mission_enums import MissionExecutionProfile
from comx_harness.shared.harness_enums.provider_enums import ProviderId
from comx_harness.shared.harness_enums.strategy_enums import (
    NativeCapability,
    StrategyFailureAction,
    StrategyNodeType,
    StrategyRunCondition,
    StrategyValidatorKind,
)


class MissionCompiler:
    """Compile one public Mission contract into bounded Strategy IR."""

    def compile(self, request: MissionRequest) -> MissionPlan:
        profile = MissionExecutionProfile(request.execution_profile)
        if profile == MissionExecutionProfile.CODEX_NATIVE:
            strategy = self._direct_strategy(request, ProviderId.CODEX)
            decisions = (
                "The caller selected the explicit codex-native execution profile.",
                "The Mission compiles to one native Codex Run and one finish gate.",
            )
        elif profile == MissionExecutionProfile.OMX_NATIVE:
            strategy = self._direct_strategy(request, ProviderId.OMX)
            decisions = (
                "The caller selected the explicit omx-native execution profile.",
                "The Mission compiles to one native OMX Run and one finish gate.",
            )
        else:
            strategy = self._review_strategy(request)
            decisions = (
                "The caller selected the explicit codex-then-omx-review profile.",
                "OMX must emit a verified blocker-report.v1 artifact.",
                "Codex resumes only when the verified blocker-count validator fails.",
                "No automatic model or Harness router was used.",
            )
        plan = MissionPlan(request=request, strategy=strategy, decisions=decisions)
        return plan

    def _direct_strategy(
        self,
        request: MissionRequest,
        provider: ProviderId,
    ) -> StrategyDefinition:
        primary = StrategyStage(
            stage_id="primary-run",
            node_type=StrategyNodeType.NATIVE_RUN,
            provider=provider,
            native_surface="exec",
            objective=self._primary_objective(request),
            workspace=request.workspace,
            expected_artifacts=request.verification.required_artifacts,
            completion_criteria=self._completion(request),
            capability_requirements=(
                NativeCapability.DETACHED_EXECUTION,
                NativeCapability.STRUCTURED_EVENTS,
                NativeCapability.ARTIFACTS,
            ),
            mutation_allowed=request.constraints.mutation_allowed,
            timeout_seconds=request.timeout_seconds,
            options=request.options,
        )
        finish = StrategyStage(
            stage_id="finish",
            node_type=StrategyNodeType.FINISH,
            objective="Finish after the primary native Run satisfies verified evidence.",
            workspace=request.workspace,
            dependencies=(primary.stage_id,),
        )
        definition = StrategyDefinition(
            strategy_id=request.mission_id,
            controller_id=request.controller_id,
            mission=request.objective,
            stages=(primary, finish),
        )
        return definition

    def _review_strategy(self, request: MissionRequest) -> StrategyDefinition:
        blocker_path = self._blocker_path(request)
        primary = StrategyStage(
            stage_id="codex-primary",
            node_type=StrategyNodeType.NATIVE_RUN,
            provider=ProviderId.CODEX,
            native_surface="exec",
            objective=self._primary_objective(request),
            workspace=request.workspace,
            expected_artifacts=request.verification.required_artifacts,
            completion_criteria=self._completion(request),
            capability_requirements=(
                NativeCapability.DETACHED_EXECUTION,
                NativeCapability.STRUCTURED_EVENTS,
                NativeCapability.ARTIFACTS,
            ),
            mutation_allowed=True,
            timeout_seconds=request.timeout_seconds,
            options=request.options,
        )
        review = StrategyStage(
            stage_id="omx-review",
            node_type=StrategyNodeType.HANDOFF,
            provider=ProviderId.OMX,
            objective=self._review_objective(request, blocker_path),
            workspace=request.workspace,
            dependencies=(primary.stage_id,),
            source_stage_id=primary.stage_id,
            input_artifacts=("result",),
            expected_artifacts=(blocker_path,),
            completion_criteria=StrategyCompletionCriteria(
                require_process_success=True,
                require_semantic_success=True,
                required_artifacts=(blocker_path,),
            ),
            capability_requirements=(NativeCapability.ARTIFACTS,),
            mutation_allowed=True,
            timeout_seconds=request.timeout_seconds,
            options=request.options,
        )
        blocker_gate = StrategyStage(
            stage_id="blocker-gate",
            node_type=StrategyNodeType.VALIDATOR,
            objective="Accept the OMX review only when verified blocker_count is zero.",
            workspace=request.workspace,
            dependencies=(review.stage_id,),
            source_stage_id=review.stage_id,
            input_artifacts=(blocker_path,),
            validator_kind=StrategyValidatorKind.BLOCKER_COUNT,
            completion_criteria=StrategyCompletionCriteria(max_blockers=0),
            failure_policy=StrategyFailurePolicy(
                action=StrategyFailureAction.CONTINUE,
                max_attempts=1,
            ),
        )
        resume = StrategyStage(
            stage_id="codex-resume",
            node_type=StrategyNodeType.NATIVE_RESUME,
            provider=ProviderId.CODEX,
            objective=self._resume_objective(request, blocker_path),
            workspace=request.workspace,
            dependencies=(primary.stage_id, blocker_gate.stage_id),
            source_stage_id=primary.stage_id,
            expected_artifacts=request.verification.required_artifacts,
            completion_criteria=self._completion(request),
            run_condition=StrategyRunCondition.ANY_DEPENDENCY_FAILED,
            capability_requirements=(
                NativeCapability.RESUME,
                NativeCapability.ARTIFACTS,
            ),
            mutation_allowed=True,
            timeout_seconds=request.timeout_seconds,
            options=request.options,
        )
        finish = StrategyStage(
            stage_id="finish",
            node_type=StrategyNodeType.FINISH,
            objective=(
                "Finish when the verified review has no blockers or the conditional "
                "Codex resume succeeds."
            ),
            workspace=request.workspace,
            dependencies=(blocker_gate.stage_id, resume.stage_id),
            run_condition=StrategyRunCondition.ANY_DEPENDENCY_SUCCEEDED,
        )
        definition = StrategyDefinition(
            strategy_id=request.mission_id,
            controller_id=request.controller_id,
            mission=request.objective,
            stages=(primary, review, blocker_gate, resume, finish),
        )
        return definition

    def _completion(self, request: MissionRequest) -> StrategyCompletionCriteria:
        completion = StrategyCompletionCriteria(
            require_process_success=request.verification.require_process_success,
            require_semantic_success=request.verification.require_semantic_success,
            required_artifacts=request.verification.required_artifacts,
        )
        return completion

    def _primary_objective(self, request: MissionRequest) -> str:
        mutation_rule = (
            "Workspace changes are allowed only when required by the objective."
            if request.constraints.mutation_allowed
            else "Do not modify the workspace."
        )
        objective = (
            f"{request.objective}\n\n"
            "Execution constraints:\n"
            f"- {mutation_rule}\n"
            "- Preserve all unrelated existing changes.\n"
            "- Do not commit.\n"
            "- Do not push.\n"
            "- Report actual verification evidence and unresolved blockers."
        )
        return objective

    def _review_objective(self, request: MissionRequest, blocker_path: str) -> str:
        objective = (
            "Independently review the verified Codex result for correctness, regressions, "
            "scope violations, and missing verification. Do not modify project source files. "
            f"Write exactly one JSON artifact to {blocker_path!r} with schema "
            "blocker-report.v1 and fields blocker_count and unresolved. Use blocker_count=0 "
            "only when no unresolved blocking issue remains. Do not commit or push."
        )
        return objective

    def _resume_objective(self, request: MissionRequest, blocker_path: str) -> str:
        objective = (
            f"Resume the original Mission and resolve every verified blocker recorded in "
            f"{blocker_path!r}. Preserve unrelated changes, rerun required verification, "
            "and do not commit or push. Original objective: "
            f"{request.objective}"
        )
        return objective

    def _blocker_path(self, request: MissionRequest) -> str:
        workspace = Path(request.workspace).expanduser().resolve()
        path = workspace / ".comx-agent" / "v2" / "mission-artifacts"
        blocker_path = path / request.mission_id / "blockers.json"
        return str(blocker_path)
