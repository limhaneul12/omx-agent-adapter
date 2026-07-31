from __future__ import annotations

from pathlib import Path

from comx_harness.application.git_policy_evidence import GitPolicyEvidenceService
from comx_harness.application.strategy_service import StrategyService
from comx_harness.schemas.git_policy_schemas import GitPolicyEvidence
from comx_harness.schemas.mission_schemas import (
    MissionArtifactReport,
    MissionEventReport,
    MissionStatusReport,
)
from comx_harness.storage.mission_store import MissionStore
from comx_harness.storage.workspace_layout import WorkspaceLayout


class MissionObservationService:
    """Project authoritative Strategy state through a durable Mission identity."""

    def __init__(
        self,
        strategies: StrategyService | None = None,
        git_policy: GitPolicyEvidenceService | None = None,
    ) -> None:
        self._strategies = strategies or StrategyService()
        self._git_policy = git_policy or GitPolicyEvidenceService()

    def status(self, workspace: str, mission_id: str) -> MissionStatusReport:
        mission = self._store(workspace).read(mission_id)
        strategy = self._strategies.status(workspace, mission.strategy_id)
        evidence = self._finalize_git_policy(workspace, mission_id)
        return MissionStatusReport(
            mission=mission,
            strategy=strategy,
            git_policy_evidence=evidence,
        )

    def events(self, workspace: str, mission_id: str) -> MissionEventReport:
        mission = self._store(workspace).read(mission_id)
        return MissionEventReport(
            mission_id=mission_id,
            strategy_events=self._strategies.events(workspace, mission.strategy_id),
        )

    def artifacts(self, workspace: str, mission_id: str) -> MissionArtifactReport:
        mission = self._store(workspace).read(mission_id)
        return MissionArtifactReport(
            mission_id=mission_id,
            strategy_artifacts=self._strategies.artifacts(
                workspace, mission.strategy_id
            ),
        )

    def _store(self, workspace: str) -> MissionStore:
        path = Path(workspace).expanduser().resolve()
        return MissionStore(WorkspaceLayout.from_workspace(path))

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
