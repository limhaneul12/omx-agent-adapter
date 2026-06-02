from pathlib import Path

from omx_remote.runtime.commands.planning.command_runtime_options import (
    runtime_options_summary_text,
)
from omx_remote.runtime.company_run.artifacts.artifact_writers import write_company_json
from omx_remote.runtime.company_run.team.worker_dispatch import (
    WORKER_BOUNDARY_SUBAGENT_RULE,
    build_worker_dispatch_payload,
)
from omx_remote.runtime.prompt_assets import render_prompt_model_asset
from omx_remote.schemas.commands.command_runtime_option_schemas import (
    CommandRuntimeOptions,
)
from omx_remote.schemas.company_run.company_run_runtime_schemas import (
    CompanyRunTeamPromptContext,
)

_PRIMARY_TEAM_OWNER_LINES: tuple[tuple[str, str], ...] = (
    (
        "alpha-surface-ui",
        "user-facing command cockpit, documentation surface, and focused "
        "tests for the objective.",
    ),
    (
        "beta-runtime-data",
        "typed status, artifact, Team, memory, command evidence, and data plumbing "
        "needed by the user-facing slice.",
    ),
    (
        "gamma-qa-security",
        "QA, security, architecture review, regression tests, and honest blockers "
        "for the implemented objective.",
    ),
    (
        "delta-integration-release",
        "integration, conflict resolution, validation, release evidence, and "
        "release-not-ready enforcement when implementation evidence is missing.",
    ),
)


def _team_owner_matrix(worker_count: int, dispatch_path: Path) -> str:
    """Render explicit native Team task-owner bullets for the company-run prompt.

    Args:
        worker_count [int]: Requested native Team worker count.
        dispatch_path [Path]: Worker-dispatches artifact path.

    Returns:
        str: Newline-delimited owner/task matrix.
    """
    lines = tuple(
        _team_owner_matrix_line(
            worker_index=worker_index,
            dispatch_path=dispatch_path,
        )
        for worker_index in range(1, worker_count + 1)
    )
    owner_matrix = "\n".join(lines)
    return owner_matrix


def _team_owner_matrix_line(worker_index: int, dispatch_path: Path) -> str:
    """Render one requested owner bullet for native Team task decomposition.

    Args:
        worker_index [int]: One-based worker index.
        dispatch_path [Path]: Worker-dispatches artifact path.

    Returns:
        str: One bullet line with a worker owner marker.
    """
    if worker_index <= len(_PRIMARY_TEAM_OWNER_LINES):
        lane_label, lane_detail = _PRIMARY_TEAM_OWNER_LINES[worker_index - 1]
    else:
        lane_label = f"extension-{worker_index}"
        lane_detail = (
            "scoped extension implementation, review, or integration support "
            "assigned by the CEO/orchestrator without taking over another worker lane."
        )
    line = (
        f"- [worker-{worker_index}] {lane_label}: {lane_detail} "
        f"Read `{dispatch_path}` for full lane boundaries."
    )
    return line


def build_team_task(
    objective: str,
    company_root: Path,
    worker_count: int = 4,
    runtime_options: CommandRuntimeOptions | None = None,
) -> str:
    """Build the OMX Team task sent by company-run.

    Args:
        objective [str]: User objective.
        company_root [Path]: Company-run artifact root.
        worker_count [int]: Requested native Team worker count.
        runtime_options [CommandRuntimeOptions | None]: Optional Codex runtime controls.

    Returns:
        str: Team task prompt.
    """
    dispatch_path = company_root / "team" / "worker-dispatches.json"
    prompt_context = CompanyRunTeamPromptContext(
        objective=objective,
        worker_count=str(worker_count),
        owner_matrix=_team_owner_matrix(
            worker_count=worker_count,
            dispatch_path=dispatch_path,
        ),
        company_root=str(company_root),
        prd_path=str(company_root / "planning" / "prd.md"),
        test_spec_path=str(company_root / "planning" / "test-spec.md"),
        execution_brief_path=str(company_root / "planning" / "execution-brief.md"),
        kickoff_path=str(company_root / "implementation" / "implementation-kickoff.md"),
        dispatch_path=str(dispatch_path),
        runtime_options=runtime_options_summary_text(runtime_options=runtime_options),
    )
    task = render_prompt_model_asset(
        parts=("company-run", "team-task.md"),
        replacements=prompt_context,
    )
    return task


def write_worker_dispatches(
    company_root: Path, objective: str, worker_count: int
) -> Path:
    """Write Team worker/subagent dispatch instructions.

    Args:
        company_root [Path]: Company-run artifact root.
        objective [str]: User objective.
        worker_count [int]: Team worker count.

    Returns:
        Path: Dispatch artifact path.
    """
    dispatch_path = company_root / "team" / "worker-dispatches.json"
    dispatch_path.parent.mkdir(parents=True, exist_ok=True)
    dispatch_payload = build_worker_dispatch_payload(
        objective=objective,
        worker_count=worker_count,
        allowed_subagents=(
            "executor",
            "test-engineer",
            "security-review",
            "code-reviewer",
        ),
        subagent_rule=WORKER_BOUNDARY_SUBAGENT_RULE,
    )
    write_company_json(dispatch_path, dispatch_payload)
    return dispatch_path

