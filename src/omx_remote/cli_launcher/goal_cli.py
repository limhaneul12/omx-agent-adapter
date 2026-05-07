import os
from collections.abc import Iterator
from contextlib import contextmanager

import typer
from pydantic import ValidationError

from omx_remote.runtime.goal.codex_goal_runtime import (
    mark_codex_goal_handoff_started,
    read_codex_goal_status,
    start_codex_goal,
)
from omx_remote.runtime.goal.codex_goal_supervisor import (
    build_goal_operating_decision,
    prepare_tracked_codex_goal_ralph_handoff_prompt,
    restore_goal_lifecycle_state,
)
from omx_remote.runtime.goal.goal_ralph_launch import (
    build_goal_ralph_launch_request,
    prepare_goal_ralph_prd_review,
)
from omx_remote.runtime.ralph.ralph_control import (
    build_ralph_launch_plan,
    format_preflight_failure,
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
from omx_remote.shared.omx_enums.codex_goal_enums import GoalRalphPrdReviewMode

GOAL_HELP_TEXT = """Start and inspect adapter-tracked native Codex Goal sessions.

Routes: Goal only for small objective loops; Goal → Ralph for structured owner planning; Goal → Ralph → Team when Ralph can split real fanout. Hypergoal is the future Goal + Ultrawork deep-work concept, not a Goal route.
"""

GOAL_TEMPLATE_TEXT = """# Codex /goal Prompt Template

Goal:
  <What should be completed, and where should the agent stop?>

Context:
  <Relevant files, directories, current state, prior decisions, and known evidence.>

Constraints:
  <Architecture rules, non-goals, safety boundaries, and testing expectations.>

Done When:
  <Concrete completion criteria, including verification commands and behavior that must not regress.>

Route guide:
  - Goal only: small, clear, single-agent task.
  - Goal → Ralph: unclear scope, PRD/owner planning, or execution structure needed.
  - Goal → Ralph → Team: Ralph can split independent worker ownership for real fanout.
  - Ralph → Team: Ralph-owned team fanout without wrapping it as a Goal route.
  - Ultrawork only: focused deep-work executor by itself.
  - Hypergoal: future Goal + Ultrawork deep-work concept; not an executor in this template.

Verification checklist:
  - Targeted tests pass.
  - Static checks pass.
  - Full test suite passes when code changed.
  - Handoff notes explain what changed, what was verified, and what remains.
"""

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

    raise ValueError(
        "execution_shape must be one of: goal_only, ralph_pipeline"
    )



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


def _parse_goal_ralph_review_mode(
    review_mode_text: str,
) -> GoalRalphPrdReviewMode:
    """Parse a Goal-to-Ralph PRD review mode from CLI text.

    Args:
        review_mode_text [str]: CLI review mode text.

    Returns:
        GoalRalphPrdReviewMode: Parsed review mode.
    """
    if review_mode_text == "llm_prompt":
        review_mode: GoalRalphPrdReviewMode = GoalRalphPrdReviewMode.LLM_PROMPT
        return review_mode
    if review_mode_text == "auto_approve":
        review_mode = GoalRalphPrdReviewMode.AUTO_APPROVE
        return review_mode

    raise ValueError("review_mode must be one of: llm_prompt, auto_approve")


@contextmanager
def _temporary_working_directory(working_directory: str) -> Iterator[None]:
    """Temporarily run launch preflight from the Goal workspace.

    Args:
        working_directory [str]: Workspace path to enter for `.omx/prd.json` reads.

    Yields:
        None: Context body runs in the workspace.

    Returns:
        Iterator[None]: Context manager iterator.
    """
    previous_working_directory: str = os.getcwd()
    os.chdir(working_directory)
    try:
        yield
    finally:
        os.chdir(previous_working_directory)


def _run_omx_command(command: list[str]):
    """Run one OMX command through the public CLI facade dependency.

    Args:
        command [list[str]]: OMX command arguments without executable name.
    """
    from omx_remote import cli as cli_facade

    command_result = cli_facade.run_omx_command(command)
    return command_result


def _run_omx_command_inherited_stdio(command: list[str]):
    """Run one OMX command while inheriting terminal stdio.

    Args:
        command [list[str]]: OMX command arguments without executable name.
    """
    from omx_remote import cli as cli_facade

    command_result = cli_facade.run_omx_command_inherited_stdio(command)
    return command_result


@goal_app.command("start")
def goal_start(
    objective: str = typer.Option(..., "--objective", help="Goal objective text to inject into native Codex Goal."),
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


@goal_app.command("prepare-ralph")
def goal_prepare_ralph(
    source_paths: list[str] = typer.Option(
        ...,
        "--source-path",
        help="Source path Ralph must read. Pass multiple times for multiple paths.",
    ),
    requested_slice: str = typer.Option(
        ...,
        "--requested-slice",
        help="One implementation slice Ralph should structure into a PRD artifact.",
    ),
    constraints: list[str] | None = typer.Option(
        None,
        "--constraint",
        help="Constraint Ralph must preserve. Pass multiple times for multiple constraints.",
    ),
    verification_expectations: list[str] = typer.Option(
        ...,
        "--verification-expectation",
        help="Verification gate Ralph must include. Pass multiple times for multiple gates.",
    ),
    cwd: str | None = typer.Option(
        None,
        "--cwd",
        help="Optional working directory whose adapter-owned goal mirror state should be read.",
    ),
) -> None:
    """Prepare a read-only Ralph PRD handoff prompt from the tracked Goal.
    
    Args:
        source_paths [list[str]]: Source paths Ralph must read.
        requested_slice [str]: Function argument.
        constraints [list[str] | None]: Optional handoff constraints.
        verification_expectations [list[str]]: Verification gates Ralph must include.
        cwd [str | None]: Function argument.
    """
    try:
        result = prepare_tracked_codex_goal_ralph_handoff_prompt(
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


@goal_app.command("launch-ralph")
def goal_launch_ralph(
    source_paths: list[str] = typer.Option(
        ...,
        "--source-path",
        help="Source path Ralph must read. Pass multiple times for multiple paths.",
    ),
    requested_slice: str = typer.Option(
        ...,
        "--requested-slice",
        help="One implementation slice to turn into a typed Ralph PRD artifact.",
    ),
    constraints: list[str] | None = typer.Option(
        None,
        "--constraint",
        help="Constraint Ralph must preserve. Pass multiple times for multiple constraints.",
    ),
    verification_expectations: list[str] = typer.Option(
        ...,
        "--verification-expectation",
        help="Verification gate Ralph must include. Pass multiple times for multiple gates.",
    ),
    review_mode: str = typer.Option(
        "llm_prompt",
        "--review-mode",
        help="PRD review gate before Ralph launch: llm_prompt or auto_approve.",
    ),
    force_cleanup: bool = typer.Option(
        False,
        "--force-cleanup",
        help="Allow launch to proceed even when known Ralph state files already exist.",
    ),
    allow_non_tty: bool = typer.Option(
        False,
        "--allow-non-tty",
        help="Allow launch from a non-interactive stdin environment when upstream behavior is acceptable.",
    ),
    inherit_stdio: bool = typer.Option(
        False,
        "--inherit-stdio",
        help="Run OMX with inherited terminal stdin/stdout/stderr for interactive Ralph startup.",
    ),
    cwd: str | None = typer.Option(
        None,
        "--cwd",
        help="Optional working directory whose adapter-owned goal mirror state should be read.",
    ),
) -> None:
    """Prepare a typed PRD from Goal state and optionally launch Ralph.

    Args:
        source_paths [list[str]]: Source paths Ralph must read.
        requested_slice [str]: Implementation slice to structure.
        constraints [list[str] | None]: Optional handoff constraints.
        verification_expectations [list[str]]: Verification gates Ralph must include.
        review_mode [str]: PRD review gate mode.
        force_cleanup [bool]: Whether stale state can be cleaned for launch.
        allow_non_tty [bool]: Whether non-TTY launch is allowed.
        inherit_stdio [bool]: Whether OMX should inherit stdio.
        cwd [str | None]: Optional Goal workspace.
    """
    try:
        parsed_review_mode: GoalRalphPrdReviewMode = _parse_goal_ralph_review_mode(
            review_mode
        )
        mirror_state = read_codex_goal_status(working_directory=cwd)
        request = build_goal_ralph_launch_request(
            mirror_state=mirror_state,
            source_paths=tuple(source_paths),
            requested_slice=requested_slice,
            constraints=tuple([] if constraints is None else constraints),
            verification_expectations=tuple(verification_expectations),
            review_mode=parsed_review_mode,
            inherit_stdio=inherit_stdio,
            force_cleanup=force_cleanup,
            allow_non_tty=allow_non_tty,
        )
        prepared_result = prepare_goal_ralph_prd_review(request)
    except (ValidationError, ValueError) as error:
        typer.echo(str(error))
        raise typer.Exit(code=2) from error

    if prepared_result.review_required:
        typer.echo(prepared_result.model_dump_json(indent=2))
        return

    try:
        with _temporary_working_directory(mirror_state.working_directory):
            command, _preflight_warnings = build_ralph_launch_plan(
                mirror_state.objective_text,
                force_cleanup=force_cleanup,
                allow_non_tty=allow_non_tty,
            )
            if inherit_stdio:
                command_result = _run_omx_command_inherited_stdio(command)
            else:
                command_result = _run_omx_command(command)
        if command_result.exit_code == 0:
            mark_codex_goal_handoff_started(
                goal_id=mirror_state.goal_id,
                working_directory=mirror_state.working_directory,
            )
        result = prepared_result.model_copy(
            update={
                "launch_attempted": True,
                "launch_blocked_reason": None,
                "command_result": command_result,
            }
        )
    except ValueError as error:
        command_result = format_preflight_failure(str(error))
        result = prepared_result.model_copy(
            update={
                "launch_attempted": True,
                "launch_blocked_reason": str(error),
                "command_result": command_result,
            }
        )
        typer.echo(result.model_dump_json(indent=2))
        raise typer.Exit(code=2) from error

    typer.echo(result.model_dump_json(indent=2))
    if command_result.exit_code != 0:
        raise typer.Exit(code=command_result.exit_code)


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
