from __future__ import annotations

from pathlib import Path

from comx_harness.controller_surface import HarnessTools
from comx_harness.schemas.execution_schemas import RunReference
from comx_harness.schemas.lifecycle_schemas import RunRecord
from comx_harness.schemas.strategy_schemas import (
    BlockerReport,
    StrategyEvidence,
    StrategyRecord,
    StrategyStage,
    StrategyStageRecord,
)
from comx_harness.shared.harness_enums.lifecycle_enums import RunStatus
from comx_harness.shared.harness_enums.strategy_enums import StrategyValidatorKind
from comx_harness.storage.json_file_store import read_json


class StrategyEvidenceEvaluator:
    """Evaluate only normalized Run state and verified Artifact evidence."""

    def __init__(self, tools: HarnessTools) -> None:
        self._tools = tools

    def run_evidence(
        self,
        stage: StrategyStage,
        run: RunRecord,
    ) -> tuple[StrategyEvidence, ...]:
        reference = RunReference(workspace=stage.workspace, run_id=run.run_id)
        state = self._tools.status(reference)
        artifacts = self._tools.artifacts(reference).artifacts
        evidence: list[StrategyEvidence] = []
        if stage.completion_criteria.require_process_success:
            evidence.append(
                StrategyEvidence(
                    kind="process_exit",
                    passed=state.record.exit_code == 0,
                    detail=f"native process exit code is {state.record.exit_code}",
                )
            )
        if stage.completion_criteria.require_semantic_success:
            evidence.append(
                StrategyEvidence(
                    kind="run_status",
                    passed=RunStatus(state.record.status) == RunStatus.SUCCEEDED,
                    detail=f"normalized Run status is {state.record.status}",
                )
            )
        required = tuple(
            artifact
            for artifact in artifacts
            if artifact.required
            or artifact.kind == "expected"
            or artifact.path in stage.completion_criteria.required_artifacts
        )
        evidence.append(
            StrategyEvidence(
                kind="required_artifacts",
                passed=bool(required)
                and all(
                    artifact.exists
                    and artifact.size_bytes > 0
                    and artifact.sha256 is not None
                    for artifact in required
                ),
                detail=(
                    f"{len(required)} required artifacts have existence, size, and digest"
                ),
            )
        )
        return tuple(evidence)

    def validator_evidence(
        self,
        record: StrategyRecord,
        stage: StrategyStage,
    ) -> tuple[StrategyEvidence, ...]:
        source_run_id = self._source_run_id(record, stage)
        source_record = self._tools.status(
            RunReference(workspace=stage.workspace, run_id=source_run_id)
        ).record
        validator_kind = StrategyValidatorKind(stage.validator_kind)
        if validator_kind == StrategyValidatorKind.RUN_EVIDENCE:
            return self.run_evidence(stage, source_record)
        if validator_kind == StrategyValidatorKind.ARTIFACT_PRESENCE:
            return self._artifact_presence(stage, source_run_id)
        return self._blocker_count(stage, source_run_id)

    def _artifact_presence(
        self,
        stage: StrategyStage,
        source_run_id: str,
    ) -> tuple[StrategyEvidence, ...]:
        artifacts = self._tools.artifacts(
            RunReference(workspace=stage.workspace, run_id=source_run_id)
        ).artifacts
        passed = bool(artifacts) and all(
            not artifact.required
            or (
                artifact.exists
                and artifact.size_bytes > 0
                and artifact.sha256 is not None
            )
            for artifact in artifacts
        )
        return (
            StrategyEvidence(
                kind="artifact_presence",
                passed=passed,
                detail="required artifacts were verified by the Run lifecycle",
            ),
        )

    def _blocker_count(
        self,
        stage: StrategyStage,
        source_run_id: str,
    ) -> tuple[StrategyEvidence, ...]:
        artifact_path = Path(stage.input_artifacts[0])
        if not artifact_path.is_absolute():
            artifact_path = Path(stage.workspace) / artifact_path
        resolved_path = artifact_path.resolve()
        artifacts = self._tools.artifacts(
            RunReference(workspace=stage.workspace, run_id=source_run_id)
        ).artifacts
        verified = next(
            (
                artifact
                for artifact in artifacts
                if Path(artifact.path).resolve() == resolved_path
                and artifact.exists
                and artifact.size_bytes > 0
                and artifact.sha256 is not None
            ),
            None,
        )
        if verified is None:
            return (
                StrategyEvidence(
                    kind="blocker_count",
                    passed=False,
                    detail=(
                        "blocker report is not a verified artifact of the source Run; "
                        "model text was not used as a substitute"
                    ),
                ),
            )
        report = BlockerReport.model_validate(read_json(resolved_path))
        return (
            StrategyEvidence(
                kind="blocker_count",
                passed=(report.blocker_count <= stage.completion_criteria.max_blockers),
                detail=(
                    f"verified blocker count is {report.blocker_count}; "
                    f"maximum allowed is {stage.completion_criteria.max_blockers}"
                ),
                digest=verified.sha256,
            ),
        )

    def _source_run_id(self, record: StrategyRecord, stage: StrategyStage) -> str:
        if stage.source_stage_id is None:
            raise ValueError(f"stage {stage.stage_id} has no source_stage_id")
        source = self._stage_record(record, stage.source_stage_id)
        if source.run_id is None:
            raise ValueError(
                f"source stage {stage.source_stage_id} has no observed run_id"
            )
        return source.run_id

    def _stage_record(
        self,
        record: StrategyRecord,
        stage_id: str,
    ) -> StrategyStageRecord:
        for stage in record.stages:
            if stage.stage_id == stage_id:
                return stage
        raise KeyError(stage_id)
