from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from comx_harness.application.strategy_service import StrategyService
from comx_harness.controller_surface import HarnessTools
from comx_harness.schemas.artifact_schemas import ArtifactReport, VerifiedArtifact
from comx_harness.schemas.execution_schemas import (
    ExecutionRequest,
    ResumeRequest,
    RunReference,
)
from comx_harness.schemas.handoff_schemas import (
    HandoffExecutionRequest,
    HandoffRecord,
    HandoffResult,
)
from comx_harness.schemas.lifecycle_schemas import (
    EventReport,
    RunRecord,
    RunState,
)
from comx_harness.schemas.provider_schemas import (
    CapabilityReport,
    ProviderCapability,
    ProviderInfo,
)
from comx_harness.schemas.strategy_schemas import StrategyDefinition, StrategyStage
from comx_harness.shared.harness_enums.lifecycle_enums import (
    ProcessLiveness,
    RunStatus,
)
from comx_harness.shared.harness_enums.provider_enums import Operation, ProviderId
from comx_harness.shared.harness_enums.strategy_enums import (
    NativeCapability,
    StrategyFailureAction,
    StrategyNodeType,
    StrategyRunCondition,
    StrategyStatus,
    StrategyValidatorKind,
)

_DIGEST = "a" * 64


class _FakeHarnessTools(HarnessTools):
    def __init__(
        self,
        *,
        workspace: Path | None = None,
        blocker_count: int | None = None,
    ) -> None:
        self.calls: list[str] = []
        self.records: dict[str, RunRecord] = {}
        self.run_sequence = 0
        self.workspace = workspace
        self.blocker_count = blocker_count

    def capabilities(self) -> CapabilityReport:
        capabilities = tuple(
            ProviderCapability(
                operation=operation,
                supported=True,
                detail="fake provider supports the contract",
            )
            for operation in (
                Operation.RUN,
                Operation.CANCEL,
                Operation.RESUME,
                Operation.ARTIFACTS,
            )
        )
        return CapabilityReport(
            providers=(
                ProviderInfo(
                    provider=ProviderId.CODEX,
                    binary="codex",
                    available=True,
                    resolved_path="/fake/codex",
                    capabilities=capabilities,
                    native_features=("exec", "resume"),
                ),
                ProviderInfo(
                    provider=ProviderId.OMX,
                    binary="omx",
                    available=True,
                    resolved_path="/fake/omx",
                    capabilities=capabilities,
                    native_features=("exec", "team", "ralph"),
                ),
            )
        )

    def run(self, request: ExecutionRequest) -> RunRecord:
        self.calls.append(f"run:{request.provider}")
        return self._new_record(ProviderId(request.provider), request.objective)

    def resume(self, request: ResumeRequest) -> RunRecord:
        source = self.records[request.run_id]
        self.calls.append(f"resume:{source.provider}")
        return self._new_record(
            ProviderId(source.provider),
            request.objective or source.objective,
            parent_run_id=source.run_id,
        )

    def handoff(self, request: HandoffExecutionRequest) -> HandoffResult:
        source = self.records[request.origin_run_id]
        self.calls.append(f"handoff:{source.provider}->{request.target_provider}")
        target = self._new_record(
            ProviderId(request.target_provider),
            request.objective,
            parent_run_id=source.run_id,
        )
        if self.workspace is not None and self.blocker_count is not None:
            blocker_path = self.workspace / "blockers.json"
            blocker_path.write_text(
                (
                    '{"schema_version":"blocker-report.v1",'
                    f'"blocker_count":{self.blocker_count},"unresolved":[]}}'
                ),
                encoding="utf-8",
            )
        artifact = self._artifacts(source)[0]
        return HandoffResult(
            handoff=HandoffRecord(
                handoff_id=f"handoff-{target.run_id}",
                created_at="2026-07-29T00:00:00Z",
                controller_id=request.controller_id,
                origin_run_id=source.run_id,
                source_provider=source.provider,
                target_provider=request.target_provider,
                source_artifact=artifact,
                target_run_id=target.run_id,
            ),
            target_run=target,
        )

    def status(self, request: RunReference) -> RunState:
        return RunState(
            record=self.records[request.run_id],
            liveness=ProcessLiveness.FINISHED,
        )

    def events(self, request: RunReference) -> EventReport:
        return EventReport(run_id=request.run_id, events=())

    def artifacts(self, request: RunReference) -> ArtifactReport:
        record = self.records[request.run_id]
        return ArtifactReport(run_id=record.run_id, artifacts=self._artifacts(record))

    def _new_record(
        self,
        provider: ProviderId,
        objective: str,
        *,
        parent_run_id: str | None = None,
    ) -> RunRecord:
        self.run_sequence += 1
        run_id = f"run-{self.run_sequence}"
        record = RunRecord(
            run_id=run_id,
            owner_controller_id="strategy-test",
            provider=provider,
            objective=objective,
            status=RunStatus.SUCCEEDED,
            plan_path=f"/fake/{run_id}/plan.json",
            pid=1000 + self.run_sequence,
            started_at="2026-07-29T00:00:00Z",
            finished_at="2026-07-29T00:00:01Z",
            exit_code=0,
            provider_session_id=f"session-{run_id}",
            parent_run_id=parent_run_id,
        )
        self.records[run_id] = record
        return record

    def _artifacts(self, record: RunRecord) -> tuple[VerifiedArtifact, ...]:
        artifacts = [
            VerifiedArtifact(
                kind="result",
                path=f"/fake/{record.run_id}/result.md",
                required=True,
                exists=True,
                size_bytes=64,
                sha256=_DIGEST,
                source_run_id=record.run_id,
                source_provider=record.provider,
            ),
            VerifiedArtifact(
                kind="plan",
                path=record.plan_path,
                required=True,
                exists=True,
                size_bytes=64,
                sha256=_DIGEST,
                source_run_id=record.run_id,
                source_provider=record.provider,
            ),
        ]
        if self.workspace is not None and record.provider == ProviderId.OMX:
            blocker_path = self.workspace / "blockers.json"
            if blocker_path.is_file():
                payload = blocker_path.read_bytes()
                artifacts.append(
                    VerifiedArtifact(
                        kind="expected",
                        path=str(blocker_path.resolve()),
                        required=True,
                        exists=True,
                        size_bytes=len(payload),
                        sha256=sha256(payload).hexdigest(),
                        source_run_id=record.run_id,
                        source_provider=record.provider,
                    )
                )
        return tuple(artifacts)


def _strategy(workspace: Path) -> StrategyDefinition:
    path = str(workspace.resolve())
    return StrategyDefinition(
        strategy_id="codex-omx-review",
        controller_id="strategy-test",
        mission="Run Codex, hand off verified evidence to OMX, then finish.",
        stages=(
            StrategyStage(
                stage_id="codex",
                node_type=StrategyNodeType.NATIVE_RUN,
                provider=ProviderId.CODEX,
                native_surface="exec",
                objective="Produce a read-only review.",
                workspace=path,
                capability_requirements=(NativeCapability.STRUCTURED_EVENTS,),
            ),
            StrategyStage(
                stage_id="omx",
                node_type=StrategyNodeType.HANDOFF,
                provider=ProviderId.OMX,
                objective="Verify the Codex review.",
                workspace=path,
                dependencies=("codex",),
                source_stage_id="codex",
                input_artifacts=("result",),
            ),
            StrategyStage(
                stage_id="validator",
                node_type=StrategyNodeType.VALIDATOR,
                objective="Require normalized status and verified artifacts.",
                workspace=path,
                dependencies=("omx",),
                source_stage_id="omx",
                validator_kind=StrategyValidatorKind.RUN_EVIDENCE,
            ),
            StrategyStage(
                stage_id="finish",
                node_type=StrategyNodeType.FINISH,
                objective="Finish after evidence passes.",
                workspace=path,
                dependencies=("validator",),
            ),
        ),
    )


def test_strategy_service_reuses_run_handoff_and_artifact_contracts(
    tmp_path: Path,
) -> None:
    tools = _FakeHarnessTools()
    service = StrategyService(tools=tools)
    definition = _strategy(tmp_path)

    record = service.execute(definition)

    assert record.status == StrategyStatus.SUCCEEDED
    assert tools.calls == ["run:codex", "handoff:codex->omx"]
    assert tuple(stage.run_id for stage in record.stages) == (
        "run-1",
        "run-2",
        None,
        None,
    )
    assert record.stages[1].handoff_id == "handoff-run-2"
    assert all(item.passed for stage in record.stages for item in stage.evidence)

    reopened = service.status(str(tmp_path), definition.strategy_id)
    events = service.events(str(tmp_path), definition.strategy_id)
    artifacts = service.artifacts(str(tmp_path), definition.strategy_id)

    assert reopened == record
    assert events.events[0].message == "created"
    assert events.events[-1].message == "succeeded"
    assert len(artifacts.artifacts) == 4
    assert {item.artifact.sha256 for item in artifacts.artifacts} == {_DIGEST}


def test_strategy_execution_is_idempotent_for_the_same_definition(
    tmp_path: Path,
) -> None:
    tools = _FakeHarnessTools()
    service = StrategyService(tools=tools)
    definition = _strategy(tmp_path)

    first = service.execute(definition)
    second = service.execute(definition)

    assert second == first
    assert tools.calls == ["run:codex", "handoff:codex->omx"]


def _blocker_branch_strategy(workspace: Path) -> StrategyDefinition:
    path = str(workspace.resolve())
    return StrategyDefinition(
        strategy_id="blocker-controlled-resume",
        controller_id="strategy-test",
        mission="Resume Codex only when verified OMX blockers exceed the limit.",
        stages=(
            StrategyStage(
                stage_id="codex",
                node_type=StrategyNodeType.NATIVE_RUN,
                provider=ProviderId.CODEX,
                native_surface="exec",
                objective="Produce a read-only implementation result.",
                workspace=path,
            ),
            StrategyStage(
                stage_id="omx-review",
                node_type=StrategyNodeType.HANDOFF,
                provider=ProviderId.OMX,
                objective="Review Codex and write blockers.json.",
                workspace=path,
                dependencies=("codex",),
                source_stage_id="codex",
                input_artifacts=("result",),
                expected_artifacts=("blockers.json",),
            ),
            StrategyStage(
                stage_id="blockers",
                node_type=StrategyNodeType.VALIDATOR,
                objective="Read the verified structured blocker report.",
                workspace=path,
                dependencies=("omx-review",),
                source_stage_id="omx-review",
                input_artifacts=("blockers.json",),
                validator_kind=StrategyValidatorKind.BLOCKER_COUNT,
                failure_policy={
                    "action": StrategyFailureAction.CONTINUE,
                    "max_attempts": 1,
                },
            ),
            StrategyStage(
                stage_id="codex-resume",
                node_type=StrategyNodeType.NATIVE_RESUME,
                provider=ProviderId.CODEX,
                objective="Resolve the verified blockers.",
                workspace=path,
                dependencies=("codex", "blockers"),
                source_stage_id="codex",
                run_condition=StrategyRunCondition.ANY_DEPENDENCY_FAILED,
            ),
            StrategyStage(
                stage_id="finish",
                node_type=StrategyNodeType.FINISH,
                objective="Finish after either clean review or successful resume.",
                workspace=path,
                dependencies=("blockers", "codex-resume"),
                run_condition=StrategyRunCondition.ANY_DEPENDENCY_SUCCEEDED,
            ),
        ),
    )


def test_strategy_resumes_codex_only_for_verified_blockers(tmp_path: Path) -> None:
    tools = _FakeHarnessTools(workspace=tmp_path, blocker_count=2)
    service = StrategyService(tools=tools)

    record = service.execute(_blocker_branch_strategy(tmp_path))

    assert record.status == StrategyStatus.SUCCEEDED
    assert tools.calls == [
        "run:codex",
        "handoff:codex->omx",
        "resume:codex",
    ]
    assert record.stages[2].status == "failed"
    assert record.stages[2].evidence[0].digest is not None
    assert record.stages[3].status == "succeeded"
    assert record.stages[4].status == "succeeded"


def test_strategy_skips_resume_when_verified_blocker_count_is_zero(
    tmp_path: Path,
) -> None:
    tools = _FakeHarnessTools(workspace=tmp_path, blocker_count=0)
    service = StrategyService(tools=tools)

    record = service.execute(_blocker_branch_strategy(tmp_path))

    assert record.status == StrategyStatus.SUCCEEDED
    assert tools.calls == ["run:codex", "handoff:codex->omx"]
    assert record.stages[2].status == "succeeded"
    assert record.stages[3].status == "skipped"
    assert record.stages[4].status == "succeeded"
