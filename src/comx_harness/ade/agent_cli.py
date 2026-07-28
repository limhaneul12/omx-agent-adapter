from __future__ import annotations

import subprocess
from pathlib import Path

import typer
from comx_harness.ade.agent_operations import AdeAgentOperations
from comx_harness.ade.agent_platform import AdeAgentTools
from comx_harness.cli_output import emit_model, fail_operation
from comx_harness.schemas.ade_agent_schemas import (
    AdoptWorkspaceRequest,
    AgentContextRequest,
    CreateWorktreeRequest,
    DetachedOperationReference,
    ProjectReference,
    RegisterProjectRequest,
    WorkspaceReference,
)
from comx_harness.schemas.ade_inspection_schemas import DetachedOperationRequest
from comx_harness.storage.json_file_store import read_json
from pydantic import ValidationError

agent_app = typer.Typer(
    help="Typed JSON application surface for trusted local agents.",
    add_completion=False,
    no_args_is_help=True,
)

_AGENT_ERRORS = (
    ValidationError,
    FileNotFoundError,
    KeyError,
    NotADirectoryError,
    ValueError,
    OSError,
    subprocess.CalledProcessError,
)


def _platform(state_root: Path | None) -> AdeAgentTools:
    return AdeAgentTools(state_root=state_root)


def _operations(state_root: Path | None) -> AdeAgentOperations:
    return AdeAgentOperations(state_root=state_root)


@agent_app.command("context")
def context_command(
    state_root: Path | None = typer.Option(None, "--state-root"),
    limit_per_workspace: int = typer.Option(25, "--limit-per-workspace"),
) -> None:
    """Read Projects, Workspaces, provider readiness, Recipes, Runs, and Attention."""
    try:
        emit_model(
            _platform(state_root).context(
                AgentContextRequest(limit_per_workspace=limit_per_workspace)
            )
        )
    except _AGENT_ERRORS as error:
        fail_operation(error)


@agent_app.command("register-project")
def register_project_command(
    path: Path = typer.Argument(...),
    name: str | None = typer.Option(None, "--name"),
    state_root: Path | None = typer.Option(None, "--state-root"),
) -> None:
    """Register a Project and adopt its root as a Workspace."""
    try:
        emit_model(
            _platform(state_root).register_project(
                RegisterProjectRequest(path=path, name=name)
            )
        )
    except _AGENT_ERRORS as error:
        fail_operation(error)


@agent_app.command("adopt-workspace")
def adopt_workspace_command(
    project_id: str = typer.Argument(...),
    path: Path = typer.Argument(...),
    name: str | None = typer.Option(None, "--name"),
    state_root: Path | None = typer.Option(None, "--state-root"),
) -> None:
    """Adopt an existing directory or related Git worktree."""
    try:
        emit_model(
            _platform(state_root).adopt_workspace(
                AdoptWorkspaceRequest(project_id=project_id, path=path, name=name)
            )
        )
    except _AGENT_ERRORS as error:
        fail_operation(error)


@agent_app.command("create-worktree")
def create_worktree_command(
    project_id: str = typer.Argument(...),
    branch: str = typer.Argument(...),
    name: str | None = typer.Option(None, "--name"),
    state_root: Path | None = typer.Option(None, "--state-root"),
) -> None:
    """Create one isolated managed Git worktree without commit or push."""
    try:
        emit_model(
            _platform(state_root).create_worktree(
                CreateWorktreeRequest(
                    project_id=project_id,
                    branch=branch,
                    name=name,
                )
            )
        )
    except _AGENT_ERRORS as error:
        fail_operation(error)


@agent_app.command("discover-worktrees")
def discover_worktrees_command(
    project_id: str = typer.Argument(...),
    state_root: Path | None = typer.Option(None, "--state-root"),
) -> None:
    """Discover Git worktrees belonging to a registered Project."""
    try:
        emit_model(
            _platform(state_root).discover_worktrees(
                ProjectReference(project_id=project_id)
            )
        )
    except _AGENT_ERRORS as error:
        fail_operation(error)


@agent_app.command("inspect-workspace")
def inspect_workspace_command(
    workspace_id: str = typer.Argument(...),
    state_root: Path | None = typer.Option(None, "--state-root"),
) -> None:
    """Read live path, Git, branch, and dirty status for one Workspace."""
    try:
        emit_model(
            _platform(state_root).inspect_workspace(
                WorkspaceReference(workspace_id=workspace_id)
            )
        )
    except _AGENT_ERRORS as error:
        fail_operation(error)


@agent_app.command("start-operation")
def start_operation_command(
    request_path: Path = typer.Argument(...),
    state_root: Path | None = typer.Option(None, "--state-root"),
) -> None:
    """Start a detached typed run, resume, or handoff request from JSON."""
    try:
        request = DetachedOperationRequest.model_validate(read_json(request_path))
        emit_model(_operations(state_root).start(request))
    except _AGENT_ERRORS as error:
        fail_operation(error)


@agent_app.command("operation")
def operation_command(
    operation_id: str = typer.Argument(...),
    state_root: Path | None = typer.Option(None, "--state-root"),
) -> None:
    """Read one detached operation record."""
    try:
        emit_model(
            _operations(state_root).read(
                DetachedOperationReference(operation_id=operation_id)
            )
        )
    except _AGENT_ERRORS as error:
        fail_operation(error)


@agent_app.command("operations")
def operations_command(
    state_root: Path | None = typer.Option(None, "--state-root"),
) -> None:
    """List detached ADE operation records newest first."""
    try:
        emit_model(_operations(state_root).list_records())
    except _AGENT_ERRORS as error:
        fail_operation(error)
