from comx_harness.application.git_policy_evidence import GitPolicyEvidenceService
from comx_harness.schemas.git_policy_schemas import GitFileState, GitSnapshot


def test_remote_change_is_not_reported_as_proven_push_attempt() -> None:
    service = GitPolicyEvidenceService()
    before = GitSnapshot(
        workspace="/workspace",
        head="abc123",
        branch="main",
        remotes=("origin local-repository (fetch)",),
        remote_refs=("refs/remotes/origin/main abc123",),
    )
    after = before.model_copy(
        update={"remote_refs": ("refs/remotes/origin/main def456",)}
    )

    evidence = service.compare("mission-001", before, after)

    assert evidence.remote_changed is True
    assert evidence.push_attempt_detected is False
    assert "cannot observe" in evidence.push_detection_basis
    assert evidence.passed is False


def test_identical_dirty_state_is_preserved_without_overclaim() -> None:
    service = GitPolicyEvidenceService()
    snapshot = GitSnapshot(
        workspace="/workspace",
        head="abc123",
        branch="main",
        files=(GitFileState(path="README.md", status=" M", sha256="digest"),),
    )

    evidence = service.compare("mission-002", snapshot, snapshot)

    assert evidence.changed_files == ()
    assert evidence.unrelated_dirty_preserved is True
    assert evidence.push_attempt_detected is False
    assert evidence.passed is True
