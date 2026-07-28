from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

from comx_harness.ade.agent_platform import AdeAgentTools
from comx_harness.controller_surface import HarnessTools
from comx_harness.schemas.ade_agent_schemas import (
    AgentContextRequest,
    CreateWorktreeRequest,
    RegisterProjectRequest,
    WorkspaceReference,
)
from comx_harness.schemas.provider_schemas import CapabilityReport


def _git(path: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ("git", "-C", str(path), *arguments),
        check=True,
        capture_output=True,
        text=True,
    )


def _repository(path: Path) -> Path:
    path.mkdir()
    _git(path, "init", "-b", "main")
    _git(path, "config", "user.email", "tests@example.com")
    _git(path, "config", "user.name", "Test User")
    (path / "README.md").write_text("initial\n", encoding="utf-8")
    _git(path, "add", "README.md")
    _git(path, "commit", "-m", "initial")
    return path


def _platform(tmp_path: Path) -> AdeAgentTools:
    tools = MagicMock(spec=HarnessTools)
    tools.capabilities.return_value = CapabilityReport(providers=())
    return AdeAgentTools(state_root=tmp_path / "state", tools=tools)


def test_agent_registers_project_and_reads_one_platform_context(tmp_path: Path) -> None:
    repository = _repository(tmp_path / "repository")
    platform = _platform(tmp_path)

    registration = platform.register_project(RegisterProjectRequest(path=repository))
    context = platform.context(AgentContextRequest())

    assert registration.project.root_path == str(repository.resolve())
    assert registration.workspace.root_path == str(repository.resolve())
    assert context.catalog.projects == (registration.project,)
    assert context.catalog.workspaces == (registration.workspace,)
    assert context.capabilities == CapabilityReport(providers=())
    assert context.capability_error is None
    assert len(context.recipes) >= 4
    assert context.workspaces[0].status.git_repository is True
    assert context.workspaces[0].runs.runs == ()
    assert context.attention_count == 0


def test_agent_creates_and_inspects_managed_worktree(tmp_path: Path) -> None:
    repository = _repository(tmp_path / "repository")
    platform = _platform(tmp_path)
    registration = platform.register_project(RegisterProjectRequest(path=repository))

    collection = platform.create_worktree(
        CreateWorktreeRequest(
            project_id=registration.project.project_id,
            branch="agent/isolated",
        )
    )
    workspace = collection.workspaces[0]
    status = platform.inspect_workspace(
        WorkspaceReference(workspace_id=workspace.workspace_id)
    )

    assert workspace.kind == "managed_worktree"
    assert status.branch == "agent/isolated"
    assert status.dirty is False
    assert status.git_repository is True
