from __future__ import annotations

from pathlib import Path

import typer
from comx_harness.ade.codex_subagent_registry import CodexSubagentRegistry
from comx_harness.cli_output import emit_model, fail_operation
from comx_harness.schemas.codex_subagent_schemas import (
    CodexSubagentRegistrationSpec,
)
from comx_harness.storage.json_file_store import read_json
from pydantic import ValidationError

codex_subagents_app = typer.Typer(
    help="Validate and register project-scoped Codex custom subagents.",
    add_completion=False,
    no_args_is_help=True,
)

_REGISTRY_ERRORS = (
    ValidationError,
    FileNotFoundError,
    NotADirectoryError,
    ValueError,
    OSError,
)


def _registry() -> CodexSubagentRegistry:
    registry = CodexSubagentRegistry()
    return registry


def _registration_spec(spec_path: Path) -> CodexSubagentRegistrationSpec:
    spec = CodexSubagentRegistrationSpec.model_validate(read_json(spec_path))
    return spec


@codex_subagents_app.command("list")
def list_command(workspace: Path = typer.Argument(...)) -> None:
    """Read project Codex subagent registrations and validation warnings."""
    try:
        emit_model(_registry().list(workspace))
    except _REGISTRY_ERRORS as error:
        fail_operation(error)


@codex_subagents_app.command("validate")
def validate_command(
    workspace: Path = typer.Argument(...),
    spec_path: Path = typer.Argument(...),
) -> None:
    """Validate one desired JSON registration spec without writing files."""
    try:
        spec = _registration_spec(spec_path)
        emit_model(_registry().validate(workspace, spec))
    except _REGISTRY_ERRORS as error:
        fail_operation(error)


@codex_subagents_app.command("register")
def register_command(
    workspace: Path = typer.Argument(...),
    spec_path: Path = typer.Argument(...),
) -> None:
    """Create or update project-local Codex custom-agent TOML files."""
    try:
        spec = _registration_spec(spec_path)
        emit_model(_registry().register(workspace, spec))
    except _REGISTRY_ERRORS as error:
        fail_operation(error)
