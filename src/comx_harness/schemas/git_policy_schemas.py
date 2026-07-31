from __future__ import annotations

from typing import Literal

from comx_harness.schemas.common_schemas import NonEmptyString, StrictModel


class GitFileState(StrictModel):
    path: NonEmptyString
    status: NonEmptyString
    sha256: NonEmptyString | None = None


class GitSnapshot(StrictModel):
    schema_version: Literal["git-snapshot.v1"] = "git-snapshot.v1"
    workspace: NonEmptyString
    head: NonEmptyString | None = None
    branch: NonEmptyString | None = None
    remotes: tuple[NonEmptyString, ...] = ()
    remote_refs: tuple[NonEmptyString, ...] = ()
    files: tuple[GitFileState, ...] = ()


class GitPolicyEvidence(StrictModel):
    schema_version: Literal["git-policy-evidence.v1"] = "git-policy-evidence.v1"
    mission_id: NonEmptyString
    before: GitSnapshot
    after: GitSnapshot
    commit_created: bool
    branch_changed: bool
    remote_changed: bool
    push_attempt_detected: bool
    push_detection_basis: NonEmptyString
    protected_files_changed: tuple[NonEmptyString, ...] = ()
    changed_files: tuple[NonEmptyString, ...] = ()
    unexpected_files: tuple[NonEmptyString, ...] = ()
    unrelated_dirty_preserved: bool
    passed: bool
