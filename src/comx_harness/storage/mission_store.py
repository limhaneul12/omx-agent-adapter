from __future__ import annotations

from comx_harness.schemas.git_policy_schemas import GitPolicyEvidence, GitSnapshot
from comx_harness.schemas.mission_schemas import MissionRecord
from comx_harness.storage.json_file_store import read_json, write_model
from comx_harness.storage.workspace_layout import WorkspaceLayout


class MissionStore:
    """Persist Mission identity and its link to the authoritative Strategy."""

    def __init__(self, layout: WorkspaceLayout) -> None:
        self.layout = layout

    def write(self, record: MissionRecord) -> MissionRecord:
        write_model(self.layout._mission_paths(record.mission_id).record, record)
        return record

    def read(self, mission_id: str) -> MissionRecord:
        return MissionRecord.model_validate(
            read_json(self.layout._mission_paths(mission_id).record)
        )

    def write_git_before(self, mission_id: str, snapshot: GitSnapshot) -> GitSnapshot:
        write_model(self.layout._mission_paths(mission_id).git_before, snapshot)
        return snapshot

    def read_git_before(self, mission_id: str) -> GitSnapshot:
        return GitSnapshot.model_validate(
            read_json(self.layout._mission_paths(mission_id).git_before)
        )

    def write_git_evidence(
        self, mission_id: str, evidence: GitPolicyEvidence
    ) -> GitPolicyEvidence:
        write_model(self.layout._mission_paths(mission_id).git_evidence, evidence)
        return evidence

    def read_git_evidence(self, mission_id: str) -> GitPolicyEvidence:
        return GitPolicyEvidence.model_validate(
            read_json(self.layout._mission_paths(mission_id).git_evidence)
        )
