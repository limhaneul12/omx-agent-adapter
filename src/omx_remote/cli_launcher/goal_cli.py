from pathlib import Path

import orjson
import typer
from pydantic import ValidationError

from omx_remote.runtime.goal.codex_goal_runtime import (
    read_codex_goal_status,
    start_codex_goal,
)
from omx_remote.runtime.goal.codex_goal_supervisor import (
    build_goal_operating_decision,
    prepare_tracked_goal_prd_authoring_prompt,
    restore_goal_lifecycle_state,
)
from omx_remote.runtime.goal.goal_lifecycle_artifacts import (
    write_goal_lifecycle_decision_from_ralph_review,
)
from omx_remote.runtime.prompt_assets import load_prompt_asset
from omx_remote.runtime.ralph.ralph_review_artifacts import (
    read_ralph_post_team_review_artifact,
)
from omx_remote.schemas.codex_goal.operating_schemas import (
    CodexGoalOperatingDecisionRequest,
)
from omx_remote.schemas.codex_goal.runtime_schemas import (
    CodexGoalExecutionShape,
    CodexGoalLaunchRequest,
    CodexGoalReviewPolicy,
    CodexGoalSpawnStatus,
)
from omx_remote.shared.utils.json_file_store import json_file_stores

GOAL_HELP_TEXT = """Start and inspect adapter-tracked native Codex Goal sessions.

Lanes: Goal only; Goal → Ralph; Goal → Ralph → Team(s); Ultrawork only; UltraGoal via native OMX; Ralph → Team. Use explicit lane status docs before treating a route as complete.
"""

GOAL_TEMPLATE_TEXT = load_prompt_asset("goal", "goal-template.md")

goal_app = typer.Typer(help=GOAL_HELP_TEXT, add_completion=False)


def _parse_goal_execution_shape(
    execution_shape_text: str,
) -> CodexGoalExecutionShape:
    """Handles parse goal execution shape.

    Args:
        execution_shape_text [str]: Function argument.

    Returns:
        CodexGoalExecutionShape: Function return value.
    """
    if execution_shape_text == "goal_only":
        execution_shape: CodexGoalExecutionShape = CodexGoalExecutionShape.GOAL_ONLY
        return execution_shape
    if execution_shape_text == "ralph_pipeline":
        execution_shape = CodexGoalExecutionShape.RALPH_PIPELINE
        return execution_shape

    raise ValueError("execution_shape must be one of: goal_only, ralph_pipeline")


def _parse_goal_review_policy(
    review_policy_text: str,
) -> CodexGoalReviewPolicy:
    """Handles parse goal review policy.

    Args:
        review_policy_text [str]: Function argument.

    Returns:
        CodexGoalReviewPolicy: Function return value.
    """
    if review_policy_text == "continue_automatically":
        review_policy: CodexGoalReviewPolicy = (
            CodexGoalReviewPolicy.CONTINUE_AUTOMATICALLY
        )
        return review_policy
    if review_policy_text == "review_required":
        review_policy = CodexGoalReviewPolicy.REVIEW_REQUIRED
        return review_policy

    raise ValueError(
        "review_policy must be one of: continue_automatically, review_required"
    )


@goal_app.command("start")
def goal_start(
    objective: str = typer.Option(
        ...,
        "--objective",
        help="Goal objective text to inject into native Codex Goal.",
    ),
    execution_shape: str = typer.Option(
        "goal_only",
        "--execution-shape",
        help="Adapter-owned execution shape for the tracked goal session.",
    ),
    review_policy: str = typer.Option(
        "continue_automatically",
        "--review-policy",
        help="Adapter-owned Ralph PRD review policy for later handoff.",
    ),
    team_worker_count: int | None = typer.Option(
        None,
        "--team-worker-count",
        help="Optional Team worker count to carry for Ralph-pipeline handoff.",
    ),
    cwd: str | None = typer.Option(
        None,
        "--cwd",
        help="Optional working directory where Codex should start and mirror state should be written.",
    ),
) -> None:
    """Start one adapter-tracked native Codex Goal session.

    Args:
        objective [str]: Function argument.
        execution_shape [str]: Function argument.
        review_policy [str]: Function argument.
        team_worker_count [int | None]: Function argument.
        cwd [str | None]: Function argument.
    """
    try:
        parsed_execution_shape: CodexGoalExecutionShape = _parse_goal_execution_shape(
            execution_shape
        )
        parsed_review_policy: CodexGoalReviewPolicy = _parse_goal_review_policy(
            review_policy
        )
        request = CodexGoalLaunchRequest(
            objective_text=objective,
            execution_shape=parsed_execution_shape,
            review_policy=parsed_review_policy,
            team_worker_count=team_worker_count,
            working_directory=cwd,
        )
        result = start_codex_goal(request)
    except (ValidationError, ValueError) as error:
        typer.echo(str(error))
        raise typer.Exit(code=2) from error

    typer.echo(result.model_dump_json(indent=2))
    if result.spawn_result.spawn_status != CodexGoalSpawnStatus.STARTED:
        raise typer.Exit(code=1)


@goal_app.command("status")
def goal_status(
    cwd: str | None = typer.Option(
        None,
        "--cwd",
        help="Optional working directory whose adapter-owned goal mirror state should be read.",
    ),
) -> None:
    """Read the latest adapter-owned native Codex Goal mirror state.

    Args:
        cwd [str | None]: Function argument.
    """
    try:
        result = read_codex_goal_status(working_directory=cwd)
    except (ValidationError, ValueError) as error:
        typer.echo(str(error))
        raise typer.Exit(code=2) from error

    typer.echo(result.model_dump_json(indent=2))


@goal_app.command("template", help="Print a lightweight Codex /goal prompt scaffold.")
def goal_template() -> None:
    """Print a lightweight Codex /goal prompt scaffold."""
    typer.echo(GOAL_TEMPLATE_TEXT)


@goal_app.command("prepare-prd-prompt")
def goal_prepare_prd_prompt(
    source_paths: list[str] = typer.Option(
        ...,
        "--source-path",
        help="Source path the Goal-scoped PRD authoring agent must read. Pass multiple times for multiple paths.",
    ),
    requested_slice: str = typer.Option(
        ...,
        "--requested-slice",
        help="One implementation slice the PRD artifact should cover.",
    ),
    constraints: list[str] | None = typer.Option(
        None,
        "--constraint",
        help="Constraint the PRD authoring agent must preserve. Pass multiple times for multiple constraints.",
    ),
    verification_expectations: list[str] = typer.Option(
        ...,
        "--verification-expectation",
        help="Verification gate the PRD artifact must include. Pass multiple times for multiple gates.",
    ),
    cwd: str | None = typer.Option(
        None,
        "--cwd",
        help="Optional working directory whose adapter-owned goal mirror state should be read.",
    ),
) -> None:
    """Prepare a Goal-scoped PRD authoring prompt from the tracked Goal.

    Args:
        source_paths [list[str]]: Source paths the authoring agent must read.
        requested_slice [str]: One implementation slice the PRD should cover.
        constraints [list[str] | None]: Optional PRD constraints.
        verification_expectations [list[str]]: Verification gates the PRD must include.
        cwd [str | None]: Optional Goal mirror workspace.
    """
    try:
        result = prepare_tracked_goal_prd_authoring_prompt(
            working_directory=cwd,
            source_paths=tuple(source_paths),
            requested_slice=requested_slice,
            constraints=tuple([] if constraints is None else constraints),
            verification_expectations=tuple(verification_expectations),
        )
    except (ValidationError, ValueError) as error:
        typer.echo(str(error))
        raise typer.Exit(code=2) from error

    typer.echo(result.model_dump_json(indent=2))


@goal_app.command("restore-lifecycle")
def goal_restore_lifecycle(
    goal_id: str = typer.Option(
        ...,
        "--goal-id",
        help="Goal identifier whose durable lifecycle artifact should be restored.",
    ),
    cwd: str | None = typer.Option(
        None,
        "--cwd",
        help="Optional working directory whose lifecycle artifact store should be read.",
    ),
) -> None:
    """Restore the durable Goal lifecycle artifact bundle and next resume target.

    Args:
        goal_id [str]: Function argument.
        cwd [str | None]: Function argument.
    """
    try:
        result = restore_goal_lifecycle_state(goal_id, working_directory=cwd)
    except (ValidationError, ValueError) as error:
        typer.echo(str(error))
        raise typer.Exit(code=2) from error

    typer.echo(result.model_dump_json(indent=2))


@goal_app.command("lifecycle-decision")
def goal_lifecycle_decision(
    goal_id: str = typer.Option(
        ...,
        "--goal-id",
        help="Goal identifier whose durable lifecycle artifact should be updated.",
    ),
    ralph_review: Path = typer.Option(
        ...,
        "--ralph-review",
        help="Path to the RalphPostTeamReviewResult JSON file.",
    ),
    cwd: str | None = typer.Option(
        None,
        "--cwd",
        help="Optional working directory whose lifecycle artifact store should be updated.",
    ),
    output_path: Path | None = typer.Option(
        None,
        "--output-path",
        help="Optional path where the lifecycle decision JSON should be written.",
    ),
) -> None:
    """Persist a Goal lifecycle decision from Ralph's post-Team review result.

    Args:
        goal_id [str]: Goal identifier whose lifecycle bundle should be updated.
        ralph_review [Path]: Path to the Ralph post-Team review JSON file.
        cwd [str | None]: Optional lifecycle artifact workspace.
        output_path [Path | None]: Optional decision JSON artifact destination.
    """
    try:
        ralph_review_result = read_ralph_post_team_review_artifact(ralph_review)
        result = write_goal_lifecycle_decision_from_ralph_review(
            goal_id,
            ralph_review_result,
            working_directory=cwd,
        )
        if output_path is not None:
            json_file_stores.for_path(output_path).write_model(result)
    except (OSError, orjson.JSONDecodeError, ValidationError, ValueError) as error:
        typer.echo(str(error))
        raise typer.Exit(code=2) from error

    typer.echo(result.model_dump_json(indent=2))


@goal_app.command("operating-decision")
def goal_operating_decision(
    goal_id: str = typer.Option(
        ...,
        "--goal-id",
        help="Goal identifier whose durable lifecycle artifact should drive the recommendation.",
    ),
    team_name: str = typer.Option(
        ...,
        "--team-name",
        help="OMX Team name to use when rendering read-only evidence commands.",
    ),
    cwd: str | None = typer.Option(
        None,
        "--cwd",
        help="Optional working directory whose lifecycle artifact store should be read.",
    ),
) -> None:
    """Recommend the next agent action from durable Goal lifecycle state.

    Args:
        goal_id [str]: Function argument.
        team_name [str]: Function argument.
        cwd [str | None]: Function argument.
    """
    try:
        restored_state = restore_goal_lifecycle_state(goal_id, working_directory=cwd)
        result = build_goal_operating_decision(
            CodexGoalOperatingDecisionRequest(
                restored_state=restored_state,
                team_name=team_name,
            )
        )
    except (ValidationError, ValueError) as error:
        typer.echo(str(error))
        raise typer.Exit(code=2) from error

    typer.echo(result.model_dump_json(indent=2))
