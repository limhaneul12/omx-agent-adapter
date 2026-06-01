import asyncio
import inspect
from pathlib import Path

import pytest
from pydantic import ValidationError

from omx_remote.runtime.operators.multi_operator import (
    MultiOperatorRegistry,
    read_live_multi_operator_snapshot,
)
from omx_remote.schemas.multi_operator_snapshot_schemas import (
    FlowInterventionRequest,
    FlowSelector,
    ManagedFlowIdCollection,
    ManagedOmxFlow,
    ManagedOmxFlowCollection,
    ManagedOmxRepo,
    ManagedOmxRepoCollection,
    MultiOperatorSnapshot,
    MultiOperatorSnapshotReadRequest,
)
from omx_remote.schemas.operator_action_schemas import (
    OperatorActionResult,
    OperatorRecoveryHint,
)
from omx_remote.schemas.runtime_status_schemas import (
    RuntimeModeStatusResult,
    RuntimeModeStatusSnapshot,
)
from omx_remote.schemas.teamwork.status_schemas import TeamStatusSnapshot


def test_managed_omx_repo_accepts_required_fields() -> None:
    result = ManagedOmxRepo.model_validate(
        {
            "repo_id": "repo-a",
            "repo_root": "/tmp/repo-a",
        }
    )

    assert result.repo_id == "repo-a"
    assert result.repo_root == "/tmp/repo-a"


def test_managed_omx_flow_rejects_empty_flow_name() -> None:
    with pytest.raises(ValidationError):
        ManagedOmxFlow.model_validate(
            {
                "flow_id": "repo-a:ralph",
                "repo_id": "repo-a",
                "flow_kind": "ralph",
                "flow_name": "",
            }
        )


def test_managed_repo_collection_rejects_duplicate_repo_ids() -> None:
    with pytest.raises(ValidationError):
        ManagedOmxRepoCollection.model_validate(
            [
                {"repo_id": "repo-a", "repo_root": "/tmp/repo-a"},
                {"repo_id": "repo-a", "repo_root": "/tmp/repo-a-copy"},
            ]
        )


def test_managed_flow_collection_rejects_duplicate_flow_ids() -> None:
    with pytest.raises(ValidationError):
        ManagedOmxFlowCollection.model_validate(
            [
                {
                    "flow_id": "repo-a:ralph",
                    "repo_id": "repo-a",
                    "flow_kind": "ralph",
                    "flow_name": "ralph",
                },
                {
                    "flow_id": "repo-a:ralph",
                    "repo_id": "repo-a",
                    "flow_kind": "team",
                    "flow_name": "team:alpha",
                    "team_name": "alpha",
                },
            ]
        )


def test_managed_flow_id_collection_rejects_duplicate_flow_ids() -> None:
    with pytest.raises(ValidationError):
        ManagedFlowIdCollection.model_validate(["repo-a:ralph", "repo-a:ralph"])


def test_multi_operator_snapshot_rejects_bucket_flow_id_missing_from_flows() -> None:
    with pytest.raises(ValidationError):
        MultiOperatorSnapshot.model_validate(
            {
                "repos": [{"repo_id": "repo-a", "repo_root": "/tmp/repo-a"}],
                "flows": [
                    {
                        "flow_id": "repo-a:ralph",
                        "repo_id": "repo-a",
                        "flow_kind": "ralph",
                        "flow_name": "ralph",
                    }
                ],
                "active_flow_ids": ["repo-a:missing"],
                "launchable_flow_ids": [],
                "resumable_flow_ids": [],
                "cleanup_flow_ids": [],
                "terminal_flow_ids": [],
            }
        )


def test_multi_operator_snapshot_collection_fields_are_required() -> None:
    required_field_names = {
        "repos",
        "flows",
        "active_flow_ids",
        "launchable_flow_ids",
        "resumable_flow_ids",
        "cleanup_flow_ids",
        "terminal_flow_ids",
    }

    for field_name in required_field_names:
        assert MultiOperatorSnapshot.model_fields[field_name].is_required()


def test_multi_operator_registry_registers_repo_and_flow() -> None:
    registry = MultiOperatorRegistry()

    registry.register_repo(ManagedOmxRepo(repo_id="repo-a", repo_root="/tmp/repo-a"))
    registry.register_flow(
        ManagedOmxFlow(
            flow_id="repo-a:ralph",
            repo_id="repo-a",
            flow_kind="ralph",
            flow_name="ralph",
        )
    )

    snapshot = registry.summarize()

    assert len(snapshot.repos) == 1
    assert len(snapshot.flows) == 1
    assert snapshot.flows[0].flow_id == "repo-a:ralph"


def test_multi_operator_registry_summarize_constructs_collection_contracts_explicitly() -> (
    None
):
    summarize_source = inspect.getsource(MultiOperatorRegistry.summarize)

    assert "ManagedOmxRepoCollection" in summarize_source
    assert "ManagedOmxFlowCollection" in summarize_source
    assert summarize_source.count("ManagedFlowIdCollection") >= 5
    assert "repos=list(self._repos.values())" not in summarize_source
    assert "flows=list(self._flows.values())" not in summarize_source


def test_multi_operator_registry_rejects_flow_for_unknown_repo() -> None:
    registry = MultiOperatorRegistry()

    with pytest.raises(ValueError):
        registry.register_flow(
            ManagedOmxFlow(
                flow_id="repo-a:ralph",
                repo_id="repo-a",
                flow_kind="ralph",
                flow_name="ralph",
            )
        )


def test_multi_operator_registry_summarizes_blocked_resumable_cleanup_and_terminal_states() -> (
    None
):
    registry = MultiOperatorRegistry()
    registry.register_repo(ManagedOmxRepo(repo_id="repo-a", repo_root="/tmp/repo-a"))
    registry.register_flow(
        ManagedOmxFlow(
            flow_id="repo-a:ralph",
            repo_id="repo-a",
            flow_kind="ralph",
            flow_name="ralph",
        )
    )
    registry.register_flow(
        ManagedOmxFlow(
            flow_id="repo-a:team-alpha",
            repo_id="repo-a",
            flow_kind="team",
            flow_name="team:alpha",
            team_name="alpha",
        )
    )
    registry.register_flow(
        ManagedOmxFlow(
            flow_id="repo-a:team-beta",
            repo_id="repo-a",
            flow_kind="team",
            flow_name="team:beta",
            team_name="beta",
        )
    )
    registry.register_flow(
        ManagedOmxFlow(
            flow_id="repo-a:team-gamma",
            repo_id="repo-a",
            flow_kind="team",
            flow_name="team:gamma",
            team_name="gamma",
        )
    )

    registry.update_flow_result(
        "repo-a:ralph",
        OperatorActionResult(
            lane="ralph",
            action="resume",
            loop_state="no_resumable_state_failure",
            next_action="launch",
            summary="need fresh launch",
            recovery_hint=OperatorRecoveryHint(
                next_action="launch",
                reason="no resumable state",
            ),
        ),
    )
    registry.update_flow_result(
        "repo-a:team-alpha",
        OperatorActionResult(
            lane="team",
            action="worker-recheck",
            loop_state="resumable_later",
            next_action="resume",
            summary="follow up later",
            recovery_hint=OperatorRecoveryHint(
                next_action="resume",
                reason="durable inbox write needs follow-up",
            ),
        ),
    )
    registry.update_flow_result(
        "repo-a:team-beta",
        OperatorActionResult(
            lane="team",
            action="cleanup",
            loop_state="stale_state_failure",
            next_action="cleanup",
            summary="needs cleanup",
            recovery_hint=OperatorRecoveryHint(
                next_action="cleanup",
                reason="stale state",
                cleanup_first=True,
            ),
        ),
    )
    registry.update_flow_result(
        "repo-a:team-gamma",
        OperatorActionResult(
            lane="team",
            action="instruction-dispatch",
            loop_state="terminal_failure",
            next_action="escalate",
            summary="failed",
            recovery_hint=OperatorRecoveryHint(
                next_action="escalate",
                reason="terminal failure",
            ),
        ),
    )

    snapshot = registry.summarize()

    assert snapshot.launchable_flow_ids == ["repo-a:ralph"]
    assert snapshot.resumable_flow_ids == ["repo-a:team-alpha"]
    assert snapshot.cleanup_flow_ids == ["repo-a:team-beta"]
    assert snapshot.terminal_flow_ids == ["repo-a:team-gamma"]


def test_multi_operator_registry_builds_flow_intervention_request_from_next_action() -> (
    None
):
    registry = MultiOperatorRegistry()
    registry.register_repo(ManagedOmxRepo(repo_id="repo-a", repo_root="/tmp/repo-a"))
    registry.register_flow(
        ManagedOmxFlow(
            flow_id="repo-a:team-alpha",
            repo_id="repo-a",
            flow_kind="team",
            flow_name="team:alpha",
            team_name="alpha",
        )
    )
    registry.update_flow_result(
        "repo-a:team-alpha",
        OperatorActionResult(
            lane="team",
            action="worker-recheck",
            loop_state="resumable_later",
            next_action="resume",
            summary="follow up later",
            recovery_hint=OperatorRecoveryHint(
                next_action="resume",
                reason="durable inbox write needs follow-up",
            ),
        ),
    )

    result = registry.build_flow_intervention_request("repo-a:team-alpha")

    assert result == FlowInterventionRequest(
        selector=FlowSelector(repo_id="repo-a", flow_id="repo-a:team-alpha"),
        requested_action="resume",
    )


def test_multi_operator_registry_returns_none_when_flow_is_only_observable() -> None:
    registry = MultiOperatorRegistry()
    registry.register_repo(ManagedOmxRepo(repo_id="repo-a", repo_root="/tmp/repo-a"))
    registry.register_flow(
        ManagedOmxFlow(
            flow_id="repo-a:team-alpha",
            repo_id="repo-a",
            flow_kind="team",
            flow_name="team:alpha",
            team_name="alpha",
        )
    )
    registry.update_flow_result(
        "repo-a:team-alpha",
        OperatorActionResult(
            lane="team",
            action="instruction-dispatch",
            loop_state="success",
            next_action="observe",
            summary="healthy",
            recovery_hint=None,
        ),
    )

    result = registry.build_flow_intervention_request("repo-a:team-alpha")

    assert result is None


def test_multi_operator_snapshot_read_request_accepts_repo_and_team_names(
    tmp_path: Path,
) -> None:
    result = MultiOperatorSnapshotReadRequest(
        repo_id="repo-a",
        repo_root=str(tmp_path),
        team_names=["alpha", "beta"],
    )

    assert result.repo_id == "repo-a"
    assert result.team_names == ("alpha", "beta")


def test_read_live_multi_operator_snapshot_reads_ralph_and_team_statuses(
    monkeypatch,
    tmp_path: Path,
) -> None:
    runtime_requests: list[str] = []
    team_requests: list[str] = []

    async def fake_read_runtime_mode_status(request):
        runtime_requests.append(request.mode)
        return RuntimeModeStatusResult(
            requested_mode=request.mode,
            found=True,
            mode_snapshot=RuntimeModeStatusSnapshot(
                name=request.mode,
                is_active=True,
                phase="starting",
                state_path=str(tmp_path / ".omx" / "state" / "ralph.json"),
            ),
        )

    async def fake_read_team_status(request):
        team_requests.append(request.team_name)
        return TeamStatusSnapshot(
            team_name=request.team_name,
            status="active",
            phase="running",
        )

    monkeypatch.setattr(
        "omx_remote.runtime.operators.multi_operator.read_runtime_mode_status",
        fake_read_runtime_mode_status,
    )
    monkeypatch.setattr(
        "omx_remote.runtime.operators.multi_operator.read_team_status",
        fake_read_team_status,
    )

    result = asyncio.run(
        read_live_multi_operator_snapshot(
            MultiOperatorSnapshotReadRequest(
                repo_id="repo-a",
                repo_root=str(tmp_path),
                team_names=["alpha"],
            )
        )
    )

    assert runtime_requests == ["ralph"]
    assert team_requests == ["alpha"]
    assert [repo.repo_id for repo in result.repos.root] == ["repo-a"]
    assert [flow.flow_id for flow in result.flows.root] == [
        "repo-a:ralph",
        "repo-a:team-alpha",
    ]
    assert result.active_flow_ids == ["repo-a:ralph", "repo-a:team-alpha"]


def test_read_live_multi_operator_snapshot_marks_inactive_ralph_launchable(
    monkeypatch,
    tmp_path: Path,
) -> None:
    async def fake_read_runtime_mode_status(request):
        return RuntimeModeStatusResult(
            requested_mode=request.mode,
            found=True,
            mode_snapshot=RuntimeModeStatusSnapshot(
                name=request.mode,
                is_active=False,
            ),
        )

    monkeypatch.setattr(
        "omx_remote.runtime.operators.multi_operator.read_runtime_mode_status",
        fake_read_runtime_mode_status,
    )

    result = asyncio.run(
        read_live_multi_operator_snapshot(
            MultiOperatorSnapshotReadRequest(
                repo_id="repo-a",
                repo_root=str(tmp_path),
                team_names=[],
            )
        )
    )

    assert result.launchable_flow_ids == ["repo-a:ralph"]
    assert result.active_flow_ids == []
