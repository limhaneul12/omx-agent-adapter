import asyncio
from dataclasses import dataclass
from pathlib import Path

from asyncer import create_task_group

from omx_remote.execution.async_boundary import run_blocking_call
from omx_remote.runtime.commands.artifacts.actual_run_record_writer import (
    ActualRunPaths,
)
from omx_remote.runtime.commands.execution.subprocess_attempt_runner import (
    run_subprocess,
    write_attempt,
)
from omx_remote.runtime.prompt_assets import render_prompt_model_asset
from omx_remote.schemas.commands.command_execution_schemas import (
    CommandFailureClassification,
    CommandStepAttempt,
)
from omx_remote.schemas.company_run_schemas import CompanyRunCouncilPromptContext
from omx_remote.shared.omx_enums.command_enums import CommandFailureKind


@dataclass(frozen=True)
class CouncilRunResult:
    """Captured evidence for one company-run council/subagent execution."""

    attempts: tuple[CommandStepAttempt, ...]
    failure: CommandFailureClassification | None


@dataclass(frozen=True)
class CouncilLaneRequest:
    """Typed parameter bundle for one independent company-run council lane."""

    paths: ActualRunPaths
    cwd: Path
    agent_name: str
    role: str
    objective: str
    artifact_label: str
    required_points: tuple[str, ...]
    output_path: Path
    timeout_seconds: float
    step_index: int
    attempt_number: int
    mode: str


def company_run_council_prompt(
    role: str,
    objective: str,
    artifact_label: str,
    required_points: tuple[str, ...],
) -> str:
    """Build a bounded Codex subagent prompt for a company-run council artifact.

    Args:
        role [str]: Council role label.
        objective [str]: User objective.
        artifact_label [str]: Artifact label to produce.
        required_points [tuple[str, ...]]: Required evidence points.

    Returns:
        str: Prompt text.
    """
    bullet_lines = "\n".join(f"- {point}" for point in required_points)
    prompt_context = CompanyRunCouncilPromptContext(
        role=role,
        objective=objective,
        artifact_label=artifact_label,
        required_points=bullet_lines,
    )
    prompt = render_prompt_model_asset(
        parts=("company-run", "council-lane.md"),
        replacements=prompt_context,
    )
    return prompt


def write_artifact_fallback(
    output_path: Path,
    role: str,
    objective: str,
    artifact_label: str,
    required_points: tuple[str, ...],
) -> None:
    """Write a deterministic council artifact when external Codex execution is disabled.

    Args:
        output_path [Path]: Artifact path.
        role [str]: Council role label.
        objective [str]: User objective.
        artifact_label [str]: Artifact label.
        required_points [tuple[str, ...]]: Required points.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    points = "\n".join(f"- {point}" for point in required_points)
    prompt_context = CompanyRunCouncilPromptContext(
        role=role,
        objective=objective,
        artifact_label=artifact_label,
        required_points=points,
    )
    text = render_prompt_model_asset(
        parts=("company-run", "council-artifact-fallback.md"),
        replacements=prompt_context,
    )
    output_path.write_text(text, encoding="utf-8")


def run_council_subagent(
    paths: ActualRunPaths,
    cwd: Path,
    agent_name: str,
    role: str,
    objective: str,
    artifact_label: str,
    required_points: tuple[str, ...],
    output_path: Path,
    timeout_seconds: float,
    step_index: int,
    attempt_number: int,
    mode: str,
) -> CouncilRunResult:
    """Run or materialize one company-run council/subagent lane.

    Args:
        paths [ActualRunPaths]: Actual run paths.
        cwd [Path]: Target repository cwd.
        agent_name [str]: Codex agent_type value.
        role [str]: Council role label.
        objective [str]: User objective.
        artifact_label [str]: Artifact label.
        required_points [tuple[str, ...]]: Required points.
        output_path [Path]: Codex final-message artifact path.
        timeout_seconds [float]: Subprocess timeout.
        step_index [int]: Step index for attempt artifacts.
        attempt_number [int]: Attempt number for this subagent lane.
        mode [str]: `codex` for real Codex execution, `artifact` for deterministic fallback.

    Returns:
        CouncilRunResult: Attempt and failure evidence.
    """
    if mode == "artifact":
        write_artifact_fallback(
            output_path=output_path,
            role=role,
            objective=objective,
            artifact_label=artifact_label,
            required_points=required_points,
        )
        result = CouncilRunResult(attempts=(), failure=None)
        return result

    prompt = company_run_council_prompt(
        role=role,
        objective=objective,
        artifact_label=artifact_label,
        required_points=required_points,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command_arguments: tuple[str, ...] = (
        "codex",
        "-c",
        f'agent_type="{agent_name}"',
        "exec",
        "--json",
        "--sandbox",
        "read-only",
        "--output-last-message",
        str(output_path),
        prompt,
    )
    outcome = run_subprocess(
        argv=command_arguments,
        cwd=cwd,
        timeout_seconds=timeout_seconds,
    )
    failure: CommandFailureClassification | None = None
    if outcome.exit_code != 0 or outcome.timed_out or not output_path.exists():
        failure = CommandFailureClassification(
            kind=CommandFailureKind.RUNTIME_CONFLICT,
            reason=f"company-run council subagent {role} did not produce {output_path}",
            retryable=True,
        )
    attempt = write_attempt(
        paths=paths,
        step_index=step_index,
        attempt=attempt_number,
        outcome=outcome,
        classification=failure,
    )
    result = CouncilRunResult(attempts=(attempt,), failure=failure)
    return result


def run_council_subagent_request(request: CouncilLaneRequest) -> CouncilRunResult:
    """Run or materialize one council lane from a shared parameter object.

    Args:
        request [CouncilLaneRequest]: Council lane request.

    Returns:
        CouncilRunResult: Attempt and failure evidence.
    """
    result = run_council_subagent(
        paths=request.paths,
        cwd=request.cwd,
        agent_name=request.agent_name,
        role=request.role,
        objective=request.objective,
        artifact_label=request.artifact_label,
        required_points=request.required_points,
        output_path=request.output_path,
        timeout_seconds=request.timeout_seconds,
        step_index=request.step_index,
        attempt_number=request.attempt_number,
        mode=request.mode,
    )
    return result


async def _run_council_lane(request: CouncilLaneRequest) -> CouncilRunResult:
    """Run one blocking council lane through the shared async boundary.

    Args:
        request [CouncilLaneRequest]: Council lane request.

    Returns:
        CouncilRunResult: Attempt and failure evidence.
    """
    result = await run_blocking_call(
        run_council_subagent_request,
        request=request,
    )
    return result


async def _run_council_lanes_async(
    requests: tuple[CouncilLaneRequest, ...],
) -> tuple[CouncilRunResult, ...]:
    """Run independent council lanes concurrently through asyncer.

    Args:
        requests [tuple[CouncilLaneRequest, ...]]: Council lane requests.

    Returns:
        tuple[CouncilRunResult, ...]: Ordered council lane results.
    """
    async with create_task_group() as task_group:
        soon_values = tuple(
            task_group.soonify(_run_council_lane)(request=request)
            for request in requests
        )
    results = tuple(soon_value.value for soon_value in soon_values)
    return results


def run_council_subagents(
    requests: tuple[CouncilLaneRequest, ...],
) -> tuple[CouncilRunResult, ...]:
    """Run independent company-run council lanes concurrently.

    Args:
        requests [tuple[CouncilLaneRequest, ...]]: Council lane requests.

    Returns:
        tuple[CouncilRunResult, ...]: Ordered council lane results.
    """
    results = asyncio.run(_run_council_lanes_async(requests=requests))
    return results
