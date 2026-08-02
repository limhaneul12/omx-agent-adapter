from __future__ import annotations

import subprocess
from pathlib import Path

import typer
from comx_harness.ade.agent_operations import AdeAgentOperations
from comx_harness.ade.agent_platform import AdeAgentTools
from comx_harness.ade.codex_subagent_cli import codex_subagents_app
from comx_harness.ade.mission_platform import (
    AdeMissionObservationTools,
    AdeMissionTools,
)
from comx_harness.ade.strategy_platform import (
    AdeStrategyObservationTools,
    AdeStrategyTools,
)
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
from comx_harness.schemas.mission_schemas import MissionRequest
from comx_harness.schemas.strategy_schemas import StrategyDefinition
from comx_harness.storage.json_file_store import read_json
from pydantic import ValidationError

agent_app = typer.Typer(
    help="Typed JSON application surface for trusted local agents.",
    add_completion=False,
    no_args_is_help=True,
)
agent_app.add_typer(codex_subagents_app, name="codex-subagents")

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


def _strategies() -> AdeStrategyTools:
    return AdeStrategyTools()


def _missions() -> AdeMissionTools:
    return AdeMissionTools()


def _mission_observations() -> AdeMissionObservationTools:
    return AdeMissionObservationTools()


def _strategy_observations() -> AdeStrategyObservationTools:
    return AdeStrategyObservationTools()


@agent_app.command("capabilities")
def capabilities_command() -> None:
    """Read provider readiness and normalized native Strategy capabilities."""
    try:
        emit_model(_strategies().capabilities())
    except _AGENT_ERRORS as error:
        fail_operation(error)


@agent_app.command("plan-mission")
def plan_mission_command(request_path: Path = typer.Argument(...)) -> None:
    """Compile one public Mission into inspectable bounded Strategy IR."""
    try:
        request = MissionRequest.model_validate(read_json(request_path))
        emit_model(_missions().plan(request))
    except _AGENT_ERRORS as error:
        fail_operation(error)


@agent_app.command("validate-mission")
def validate_mission_command(request_path: Path = typer.Argument(...)) -> None:
    """Validate one Mission and its compiled Strategy without executing it."""
    try:
        request = MissionRequest.model_validate(read_json(request_path))
        emit_model(_missions().validate(request))
    except _AGENT_ERRORS as error:
        fail_operation(error)


@agent_app.command("execute-mission")
def execute_mission_command(
    request_path: Path = typer.Argument(...),
    foreground: bool = typer.Option(False, "--foreground"),
) -> None:
    """Start a Mission through the shared Strategy Runtime, detached by default."""
    try:
        request = MissionRequest.model_validate(read_json(request_path))
        missions = _missions()
        result = (
            missions.execute_foreground(request)
            if foreground
            else missions.execute(request)
        )
        emit_model(result)
    except _AGENT_ERRORS as error:
        fail_operation(error)


@agent_app.command("mission-status")
def mission_status_command(
    workspace: Path = typer.Argument(...),
    mission_id: str = typer.Argument(...),
) -> None:
    """Read Mission identity and its authoritative Strategy projection."""
    try:
        emit_model(_mission_observations().status(str(workspace), mission_id))
    except _AGENT_ERRORS as error:
        fail_operation(error)


@agent_app.command("mission-events")
def mission_events_command(
    workspace: Path = typer.Argument(...),
    mission_id: str = typer.Argument(...),
) -> None:
    """Read ordered Strategy events through the Mission identity."""
    try:
        emit_model(_mission_observations().events(str(workspace), mission_id))
    except _AGENT_ERRORS as error:
        fail_operation(error)


@agent_app.command("mission-artifacts")
def mission_artifacts_command(
    workspace: Path = typer.Argument(...),
    mission_id: str = typer.Argument(...),
) -> None:
    """Read verified Strategy and Run artifacts through the Mission identity."""
    try:
        emit_model(_mission_observations().artifacts(str(workspace), mission_id))
    except _AGENT_ERRORS as error:
        fail_operation(error)


@agent_app.command("validate-strategy")
def validate_strategy_command(request_path: Path = typer.Argument(...)) -> None:
    """Validate advanced or debug Strategy IR without executing it."""
    try:
        definition = StrategyDefinition.model_validate(read_json(request_path))
        emit_model(_strategies().validate(definition))
    except _AGENT_ERRORS as error:
        fail_operation(error)


@agent_app.command("execute-strategy")
def execute_strategy_command(
    request_path: Path = typer.Argument(...),
    foreground: bool = typer.Option(False, "--foreground"),
) -> None:
    """Start advanced or debug Strategy IR in a detached worker by default."""
    try:
        definition = StrategyDefinition.model_validate(read_json(request_path))
        strategies = _strategies()
        result = (
            strategies.execute_foreground(definition)
            if foreground
            else strategies.execute(definition)
        )
        emit_model(result)
    except _AGENT_ERRORS as error:
        fail_operation(error)


@agent_app.command("strategy-launch")
def strategy_launch_command(
    workspace: Path = typer.Argument(...),
    strategy_id: str = typer.Argument(...),
) -> None:
    """Read the detached worker launch envelope for one Strategy."""
    try:
        emit_model(_strategy_observations().launch_status(str(workspace), strategy_id))
    except _AGENT_ERRORS as error:
        fail_operation(error)


@agent_app.command("strategy-status")
def strategy_status_command(
    workspace: Path = typer.Argument(...),
    strategy_id: str = typer.Argument(...),
) -> None:
    """Read the durable Runtime state for one Strategy."""
    try:
        emit_model(_strategy_observations().status(str(workspace), strategy_id))
    except _AGENT_ERRORS as error:
        fail_operation(error)


@agent_app.command("strategy-events")
def strategy_events_command(
    workspace: Path = typer.Argument(...),
    strategy_id: str = typer.Argument(...),
) -> None:
    """Read ordered durable Strategy events."""
    try:
        emit_model(_strategy_observations().events(str(workspace), strategy_id))
    except _AGENT_ERRORS as error:
        fail_operation(error)


@agent_app.command("strategy-artifacts")
def strategy_artifacts_command(
    workspace: Path = typer.Argument(...),
    strategy_id: str = typer.Argument(...),
) -> None:
    """Read verified Run artifacts associated with one Strategy."""
    try:
        emit_model(_strategy_observations().artifacts(str(workspace), strategy_id))
    except _AGENT_ERRORS as error:
        fail_operation(error)


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
