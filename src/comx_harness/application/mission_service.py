from __future__ import annotations

from pathlib import Path

from comx_harness.application.git_policy_evidence import GitPolicyEvidenceService
from comx_harness.application.mission_compiler import MissionCompiler
from comx_harness.application.strategy_service import StrategyService
from comx_harness.schemas.git_policy_schemas import GitPolicyEvidence
from comx_harness.schemas.mission_schemas import (
    MissionPlan,
    MissionRecord,
    MissionRequest,
    MissionValidationReport,
)
from comx_harness.schemas.strategy_schemas import StrategyRecord
from comx_harness.storage.mission_store import MissionStore
from comx_harness.storage.time_identity import utc_timestamp
from comx_harness.storage.workspace_layout import WorkspaceLayout


class MissionService:
    """Plan and execute public Missions through the existing Strategy Runtime."""

    def __init__(
        self,
        compiler: MissionCompiler | None = None,
        strategies: StrategyService | None = None,
        git_policy: GitPolicyEvidenceService | None = None,
    ) -> None:
        self._compiler = compiler or MissionCompiler()
        self._strategies = strategies or StrategyService()
        self._git_policy = git_policy or GitPolicyEvidenceService()

    def plan(self, request: MissionRequest) -> MissionPlan:
        plan = self._compiler.compile(request)
        return plan

    def validate(self, request: MissionRequest) -> MissionValidationReport:
        plan = self.plan(request)
        strategy_validation = self._strategies.validate(plan.strategy)
        report = MissionValidationReport(
            mission_id=request.mission_id,
            valid=strategy_validation.valid,
            plan=plan,
            strategy_validation=strategy_validation,
        )
        return report

    def execute(self, request: MissionRequest) -> StrategyRecord:
        validation = self.validate(request)
        if not validation.valid:
            details = "; ".join(
                issue.detail for issue in validation.strategy_validation.issues
            )
            raise ValueError(f"mission validation failed: {details}")
        self.register(request, validation.plan)
        try:
            record = self._strategies.execute(validation.plan.strategy)
        finally:
            self._finalize_git_policy(request.workspace, request.mission_id)
        return record

    def register(
        self, request: MissionRequest, plan: MissionPlan | None = None
    ) -> MissionRecord:
        resolved_plan = plan or self.plan(request)
        store = self._store(request.workspace)
        existing = self._existing_record(store, request)
        if existing is not None:
            return existing
        timestamp = utc_timestamp()
        record = store.write(
            MissionRecord(
                mission_id=request.mission_id,
                request=request,
                strategy_id=resolved_plan.strategy.strategy_id,
                created_at=timestamp,
                updated_at=timestamp,
            )
        )
        store.write_git_before(
            request.mission_id, self._git_policy.snapshot(request.workspace)
        )
        return record

    def _store(self, workspace: str) -> MissionStore:
        path = Path(workspace).expanduser().resolve()
        return MissionStore(WorkspaceLayout.from_workspace(path))

    def _existing_record(
        self, store: MissionStore, request: MissionRequest
    ) -> MissionRecord | None:
        try:
            existing = store.read(request.mission_id)
        except FileNotFoundError:
            return None
        if existing.request != request:
            raise ValueError(
                f"mission_id {request.mission_id!r} already has another request"
            )
        return existing

    def _finalize_git_policy(
        self, workspace: str, mission_id: str
    ) -> GitPolicyEvidence | None:
        store = self._store(workspace)
        try:
            before = store.read_git_before(mission_id)
        except FileNotFoundError:
            return None
        after = self._git_policy.snapshot(workspace)
        evidence = self._git_policy.compare(mission_id, before, after)
        return store.write_git_evidence(mission_id, evidence)
