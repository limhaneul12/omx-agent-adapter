from pathlib import Path

import orjson

from omx_remote.schemas.codex_goal.runtime_schemas import CodexGoalMirrorState
from omx_remote.schemas.codex_goal.supervisor_schemas import (
    GoalRalphLaunchRequest,
    GoalRalphLaunchResult,
)
from omx_remote.schemas.ralph.prd_schemas import RalphPrdArtifact
from omx_remote.shared.omx_enums.codex_goal_enums import (
    CodexGoalExecutionShape,
    GoalRalphPrdReviewMode,
)
from omx_remote.shared.omx_enums.ralph_enums import RalphPrdContinuationPolicy


def _resolve_workspace_path(mirror_state: CodexGoalMirrorState) -> Path:
    """Resolve the workspace path owned by one Goal mirror state.

    Args:
        mirror_state [CodexGoalMirrorState]: Goal mirror state carrying the workspace.

    Returns:
        Path: Absolute workspace path.
    """
    workspace_path = Path(mirror_state.working_directory).resolve()
    return workspace_path


def _build_continuation_policy(
    review_mode: GoalRalphPrdReviewMode,
) -> RalphPrdContinuationPolicy:
    """Map a Goal review mode onto Ralph's typed continuation policy.

    Args:
        review_mode [GoalRalphPrdReviewMode]: Requested PRD review gate.

    Returns:
        RalphPrdContinuationPolicy: PRD continuation policy.
    """
    if review_mode == GoalRalphPrdReviewMode.LLM_PROMPT:
        continuation_policy = RalphPrdContinuationPolicy.REVIEW_REQUIRED
        return continuation_policy

    continuation_policy = RalphPrdContinuationPolicy.CONTINUE_AUTOMATICALLY
    return continuation_policy


def build_goal_ralph_launch_request(
    mirror_state: CodexGoalMirrorState,
    source_paths: tuple[str, ...],
    requested_slice: str,
    constraints: tuple[str, ...],
    verification_expectations: tuple[str, ...],
    review_mode: GoalRalphPrdReviewMode,
    inherit_stdio: bool,
    force_cleanup: bool,
    allow_non_tty: bool,
) -> GoalRalphLaunchRequest:
    """Build a typed Goal-to-Ralph launch request from CLI/runtime inputs.

    Args:
        mirror_state [CodexGoalMirrorState]: Persisted Goal mirror state.
        source_paths [tuple[str, ...]]: Source files/directories Ralph must read.
        requested_slice [str]: Implementation slice for the PRD.
        constraints [tuple[str, ...]]: Constraints to preserve.
        verification_expectations [tuple[str, ...]]: Verification commands/expectations.
        review_mode [GoalRalphPrdReviewMode]: PRD review behavior.
        inherit_stdio [bool]: Whether Ralph launch should inherit terminal stdio.
        force_cleanup [bool]: Whether launch can proceed through stale state.
        allow_non_tty [bool]: Whether non-TTY launch is allowed.

    Returns:
        GoalRalphLaunchRequest: Typed request.
    """
    if mirror_state.execution_shape != CodexGoalExecutionShape.RALPH_PIPELINE:
        raise ValueError("Goal launch-ralph requires a goal with execution_shape=ralph_pipeline.")

    request = GoalRalphLaunchRequest(
        mirror_state=mirror_state,
        source_paths=source_paths,
        requested_slice=requested_slice,
        constraints=constraints,
        verification_expectations=verification_expectations,
        review_mode=review_mode,
        inherit_stdio=inherit_stdio,
        force_cleanup=force_cleanup,
        allow_non_tty=allow_non_tty,
    )
    return request


def build_goal_ralph_prd_artifact(request: GoalRalphLaunchRequest) -> RalphPrdArtifact:
    """Build the typed `.omx/prd.json` artifact for a Goal-to-Ralph bridge.

    Args:
        request [GoalRalphLaunchRequest]: Typed Goal-to-Ralph request.

    Returns:
        RalphPrdArtifact: Typed Ralph PRD artifact.
    """
    continuation_policy: RalphPrdContinuationPolicy = _build_continuation_policy(
        request.review_mode
    )
    scope: tuple[str, ...] = (
        request.requested_slice,
        *tuple(f"source: {source_path}" for source_path in request.source_paths),
    )
    execution_plan: tuple[str, ...] = (
        "Review the typed Ralph PRD artifact before execution when the review gate requires it.",
        "Launch Ralph with the PRD objective after the artifact is approved or auto-approved.",
        "Ralph owns implementation planning and execution for the requested slice only.",
    )
    artifact = RalphPrdArtifact(
        objective=request.mirror_state.objective_text,
        scope=scope,
        constraints=request.constraints,
        execution_plan=execution_plan,
        verification_expectations=request.verification_expectations,
        requires_team_fanout=False,
        continuation_policy=continuation_policy,
    )
    return artifact


def _write_prd_artifact(workspace_path: Path, artifact: RalphPrdArtifact) -> Path:
    """Write one typed Ralph PRD artifact under the workspace `.omx` directory.

    Args:
        workspace_path [Path]: Goal workspace root.
        artifact [RalphPrdArtifact]: PRD artifact to persist.

    Returns:
        Path: Written PRD path.
    """
    prd_path = workspace_path / ".omx" / "prd.json"
    prd_path.parent.mkdir(parents=True, exist_ok=True)
    prd_path.write_bytes(orjson.dumps(artifact.model_dump(mode="json"), option=orjson.OPT_INDENT_2))
    return prd_path


def _render_llm_review_prompt(
    request: GoalRalphLaunchRequest,
    artifact: RalphPrdArtifact,
) -> str:
    """Render a copy-pasteable LLM review prompt for a Ralph PRD artifact.

    Args:
        request [GoalRalphLaunchRequest]: Typed Goal-to-Ralph request.
        artifact [RalphPrdArtifact]: Draft Ralph PRD artifact.

    Returns:
        str: Markdown review prompt.
    """
    artifact_json = orjson.dumps(
        artifact.model_dump(mode="json"),
        option=orjson.OPT_INDENT_2,
    ).decode()
    source_lines = "\n".join(f"- {source_path}" for source_path in request.source_paths)
    verification_lines = "\n".join(
        f"- {expectation}" for expectation in request.verification_expectations
    )
    constraint_lines = "\n".join(
        f"- {constraint}" for constraint in request.constraints
    )
    if constraint_lines == "":
        constraint_lines = "- No additional constraints supplied."

    prompt = f"""# LLM Ralph PRD Review

Review the draft Ralph PRD before `agent-remote` launches Ralph for this Goal.

Goal ID: {request.mirror_state.goal_id}
Goal objective: {request.mirror_state.objective_text}
Requested slice: {request.requested_slice}

Source paths Ralph must respect:
{source_lines}

Constraints:
{constraint_lines}

Verification expectations:
{verification_lines}

Approve only if:
- The PRD objective exactly matches the Goal objective.
- Scope is limited to the requested slice and source paths.
- Verification expectations are concrete enough for an agent to run.
- The PRD does not request Team fanout unless the slice genuinely requires it.
- Ralph can execute independently after approval.

Return this JSON shape only:
```json
{{
  "decision": "approve | revise",
  "launch_ready": false,
  "blockers": [],
  "required_changes": [],
  "review_summary": "short reason"
}}
```

Draft `.omx/prd.json`:
```json
{artifact_json}
```
""".strip()
    return prompt


def _write_llm_review_prompt(
    workspace_path: Path,
    request: GoalRalphLaunchRequest,
    artifact: RalphPrdArtifact,
) -> Path:
    """Write a durable LLM PRD review prompt for human/LLM approval.

    Args:
        workspace_path [Path]: Goal workspace root.
        request [GoalRalphLaunchRequest]: Typed Goal-to-Ralph request.
        artifact [RalphPrdArtifact]: Draft Ralph PRD artifact.

    Returns:
        Path: Written review prompt path.
    """
    review_path = (
        workspace_path
        / ".agent-remote"
        / "reviews"
        / f"{request.mirror_state.goal_id}-ralph-prd-review.md"
    )
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_prompt = _render_llm_review_prompt(request, artifact)
    review_path.write_text(review_prompt)
    return review_path


def prepare_goal_ralph_prd_review(request: GoalRalphLaunchRequest) -> GoalRalphLaunchResult:
    """Prepare `.omx/prd.json` and optional LLM review prompt for Goal-to-Ralph launch.

    Args:
        request [GoalRalphLaunchRequest]: Typed Goal-to-Ralph request.

    Returns:
        GoalRalphLaunchResult: Preparation result. Launch itself is handled by the CLI layer.
    """
    workspace_path: Path = _resolve_workspace_path(request.mirror_state)
    artifact: RalphPrdArtifact = build_goal_ralph_prd_artifact(request)
    prd_path: Path = _write_prd_artifact(workspace_path, artifact)

    review_required: bool = request.review_mode == GoalRalphPrdReviewMode.LLM_PROMPT
    review_prompt_path: Path | None = None
    launch_blocked_reason: str | None = None
    if review_required:
        review_prompt_path = _write_llm_review_prompt(
            workspace_path=workspace_path,
            request=request,
            artifact=artifact,
        )
        launch_blocked_reason = "Ralph PRD requires LLM review before launch."

    result = GoalRalphLaunchResult(
        goal_id=request.mirror_state.goal_id,
        prd_path=str(prd_path),
        review_required=review_required,
        review_prompt_path=None if review_prompt_path is None else str(review_prompt_path),
        launch_attempted=False,
        launch_blocked_reason=launch_blocked_reason,
        ralph_prd_artifact=artifact,
    )
    return result
