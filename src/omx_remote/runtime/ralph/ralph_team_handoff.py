from datetime import UTC, datetime
from pathlib import Path

import orjson

from omx_remote.adapter_types.ralph_types import (
    RalphTeamDagAdminPolicyPayload,
    RalphTeamDagNodePayload,
    RalphTeamDagPayload,
    RalphTeamDagWorkerPolicyPayload,
    RalphWorkerAuthorizationPayload,
)
from omx_remote.schemas.ralph.prd_schemas import RalphPrdArtifact, TeamWorkerAssignment
from omx_remote.shared.utils.omx_task import quote_omx_task


def format_markdown_list(values: tuple[str, ...] | list[str]) -> str:
    """Formats string values as a markdown list.

    Args:
        values [tuple[str, ...] | list[str]]: Values that should become markdown bullets.

    Returns:
        str: Markdown bullet list, or `- none` for empty inputs.
    """
    if not values:
        return "- none"
    return "\n".join(f"- {value}" for value in values)


def allocator_hint_file_paths(assignment: TeamWorkerAssignment) -> list[str]:
    """Return file paths that should bias OMX worker allocation.

    Ralph-owned internal report artifacts are deliverables, not product-code or
    repo-scope ownership hints. Passing them to OMX's DAG allocator makes every
    evidence lane look like the same `.omx`/`.comx-agent` domain and can group
    independent worker assignments onto worker-1.

    Args:
        assignment [TeamWorkerAssignment]: Typed worker assignment from the Ralph PRD artifact.

    Returns:
        list[str]: Owned paths that should be visible as OMX allocation hints.
    """
    return [
        path
        for path in assignment.owned_files
        if not path.startswith(".omx/") and not path.startswith(".comx-agent/")
    ]


def uses_internal_only_owned_files(assignment: TeamWorkerAssignment) -> bool:
    """Return whether the assignment only owns agent/runtime-internal artifacts.

    Args:
        assignment [TeamWorkerAssignment]: Typed worker assignment from the Ralph PRD artifact.

    Returns:
        bool: True when all owned files are internal agent/runtime artifacts.
    """
    return len(assignment.owned_files) > 0 and not allocator_hint_file_paths(assignment)


def allocator_task_role(assignment: TeamWorkerAssignment) -> str:
    """Return the DAG task role used by OMX's allocator.

    `omx team` uses task role as an allocation signal. Ralph PRD assignments are
    already worker-specific, so use the worker id as the role to keep assignment
    lanes separated when the launch command leaves agent type implicit.

    Args:
        assignment [TeamWorkerAssignment]: Typed worker assignment from the Ralph PRD artifact.

    Returns:
        str: Worker-specific role value for the DAG node.
    """
    return assignment.worker_id


def allocator_task_description(assignment: TeamWorkerAssignment) -> str:
    """Return a concise DAG description that avoids cross-worker hint collisions.

    Args:
        assignment [TeamWorkerAssignment]: Typed worker assignment from the Ralph PRD artifact.

    Returns:
        str: DAG node description optimized for OMX allocation.
    """
    if uses_internal_only_owned_files(assignment):
        return f"{assignment.worker_id}: {assignment.lane_name}. See PRD."
    return render_worker_assignment_description(assignment)


def allocator_task_acceptance(assignment: TeamWorkerAssignment) -> list[str]:
    """Return acceptance hints that should enter OMX allocator-visible task text.

    Args:
        assignment [TeamWorkerAssignment]: Typed worker assignment from the Ralph PRD artifact.

    Returns:
        list[str]: Acceptance strings safe to expose to the allocator.
    """
    if uses_internal_only_owned_files(assignment):
        return []
    return [
        *assignment.verification_commands,
        assignment.handoff_summary_required,
    ]


def render_worker_assignment_description(assignment: TeamWorkerAssignment) -> str:
    """Renders one Team worker assignment description for Ralph DAG handoff.

    Args:
        assignment [TeamWorkerAssignment]: Typed worker assignment from the Ralph PRD artifact.

    Returns:
        str: Human-readable worker assignment description.
    """
    description: str = f"""Lane: {assignment.lane_name}
Objective: {assignment.objective}

Owned files:
{format_markdown_list(assignment.owned_files)}

Read-only context files:
{format_markdown_list(assignment.read_only_context_files)}

Forbidden files / coordination notes:
{format_markdown_list(assignment.forbidden_files)}

TDD steps:
{format_markdown_list(assignment.tdd_steps)}

Verification commands:
{format_markdown_list(assignment.verification_commands)}

Handoff summary required:
- {assignment.handoff_summary_required}

Authorization policy: {assignment.authorization_policy}

Allowed commands:
{format_markdown_list(assignment.authorization_scope.allowed_commands)}

Forbidden commands:
{format_markdown_list(assignment.authorization_scope.forbidden_commands)}

Requires human approval for:
{format_markdown_list(assignment.authorization_scope.requires_human_for)}

Requires LLM review for:
{format_markdown_list(assignment.authorization_scope.requires_llm_review_for)}
""".strip()
    return description


def build_worker_authorization_payload(
    assignment: TeamWorkerAssignment,
) -> RalphWorkerAuthorizationPayload:
    """Builds typed Team DAG authorization payload for one worker assignment.

    Args:
        assignment [TeamWorkerAssignment]: Typed worker assignment from the Ralph PRD artifact.

    Returns:
        RalphWorkerAuthorizationPayload: Stable authorization payload embedded in the Team DAG.
    """
    authorization_payload: RalphWorkerAuthorizationPayload = (
        RalphWorkerAuthorizationPayload(
            policy=assignment.authorization_policy,
            allowed_commands=list(assignment.authorization_scope.allowed_commands),
            forbidden_commands=list(assignment.authorization_scope.forbidden_commands),
            requires_human_for=list(assignment.authorization_scope.requires_human_for),
            requires_llm_review_for=list(
                assignment.authorization_scope.requires_llm_review_for
            ),
        )
    )
    return authorization_payload


def build_team_admin_policy_payload(
    ralph_prd_artifact: RalphPrdArtifact,
) -> RalphTeamDagAdminPolicyPayload:
    """Builds typed Team Admin policy payload from a Ralph PRD artifact.

    Args:
        ralph_prd_artifact [RalphPrdArtifact]: Typed Ralph PRD artifact that owns the Team Admin contract.

    Returns:
        RalphTeamDagAdminPolicyPayload: Stable Team Admin policy payload embedded in the DAG.

    Raises:
        ValueError: Raised when the PRD is missing the Team Admin contract.
    """
    team_admin = ralph_prd_artifact.team_admin
    if team_admin is None:
        raise ValueError(
            "The typed Ralph PRD artifact requires Team fanout but does not declare a Team Admin contract."
        )

    admin_policy_payload: RalphTeamDagAdminPolicyPayload = (
        RalphTeamDagAdminPolicyPayload(
            admin_id=team_admin.admin_id,
            aggregation_policy=team_admin.aggregation_policy,
            merge_policy=team_admin.merge_policy,
            completion_policy=team_admin.completion_policy,
            requires_human_for=list(team_admin.requires_human_for),
            requires_llm_review_for=list(team_admin.requires_llm_review_for),
            final_report_required=team_admin.final_report_required,
        )
    )
    return admin_policy_payload


def planning_artifact_slug() -> str:
    """Builds a timestamped Ralph Team planning artifact slug.

    Returns:
        str: UTC timestamp slug ending in `-ralph-team`.
    """
    timestamp: str = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    slug: str = f"{timestamp}-ralph-team"
    return slug


def write_ralph_team_dag_handoff_artifacts(
    ralph_prd_artifact: RalphPrdArtifact,
    canonical_launch_task: str,
    team_worker_count: int,
    workspace_root: Path,
) -> None:
    """Writes Ralph Team PRD, test spec, and typed DAG handoff artifacts.

    Args:
        ralph_prd_artifact [RalphPrdArtifact]: Typed Ralph PRD artifact that requires Team fanout.
        canonical_launch_task [str]: Canonical launch task resolved from the typed PRD artifact.
        team_worker_count [int]: Requested Team worker count.
        workspace_root [Path]: Workspace root containing `.omx/plans`.

    Raises:
        ValueError: Raised when Team fanout assignments are missing.
    """
    assignments: tuple[TeamWorkerAssignment, ...] | None = (
        ralph_prd_artifact.team_worker_assignments
    )
    if assignments is None:
        raise ValueError(
            "The typed Ralph PRD artifact requires Team fanout but does not declare Team worker assignments."
        )

    plans_dir: Path = workspace_root / ".omx" / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)

    artifact_slug: str = planning_artifact_slug()
    prd_name: str = f"prd-{artifact_slug}.md"
    test_spec_name: str = f"test-spec-{artifact_slug}.md"
    dag_name: str = f"team-dag-{artifact_slug}.json"
    launch_hint: str = (
        f"omx team {team_worker_count} {quote_omx_task(canonical_launch_task)}"
    )

    prd_lines: list[str] = [
        "# Ralph Team PRD Handoff",
        "",
        f"Launch via {launch_hint}",
        "",
        "## Objective",
        canonical_launch_task,
        "",
        "## Scope",
        format_markdown_list(ralph_prd_artifact.scope),
        "",
        "## Constraints",
        format_markdown_list(ralph_prd_artifact.constraints),
        "",
        "## Execution Plan",
        format_markdown_list(ralph_prd_artifact.execution_plan),
        "",
        "## Verification Expectations",
        format_markdown_list(ralph_prd_artifact.verification_expectations),
        "",
        "## Worker Assignments",
        "",
        *[
            f"### {assignment.worker_id}: {assignment.lane_name}\n\n"
            f"{render_worker_assignment_description(assignment)}\n"
            for assignment in assignments
        ],
        "## Team DAG Handoff",
        "```json",
    ]
    worker_policy_payload: RalphTeamDagWorkerPolicyPayload = (
        RalphTeamDagWorkerPolicyPayload(
            requested_count=team_worker_count,
            count_source="plan-suggested",
            strict_max_count=True,
        )
    )
    node_payloads: list[RalphTeamDagNodePayload] = [
        RalphTeamDagNodePayload(
            id=assignment.worker_id,
            subject=assignment.lane_name,
            description=allocator_task_description(assignment),
            role=allocator_task_role(assignment),
            owner=assignment.worker_id,
            lane=assignment.lane_name,
            filePaths=allocator_hint_file_paths(assignment),
            depends_on=[],
            authorization=build_worker_authorization_payload(assignment),
            acceptance=allocator_task_acceptance(assignment),
        )
        for assignment in assignments
    ]
    dag_payload: RalphTeamDagPayload = RalphTeamDagPayload(
        schema_version=1,
        plan_slug=artifact_slug,
        source_prd=prd_name,
        worker_policy=worker_policy_payload,
        admin_policy=build_team_admin_policy_payload(ralph_prd_artifact),
        nodes=node_payloads,
    )
    dag_text: str = orjson.dumps(dag_payload, option=orjson.OPT_INDENT_2).decode()
    prd_lines.extend([dag_text, "```", ""])

    test_spec_lines: list[str] = [
        "# Ralph Team Test Spec",
        "",
        "The approved Ralph Team PRD requires every worker lane to follow RED -> GREEN -> verification.",
        "",
        "## Required verification",
        format_markdown_list(ralph_prd_artifact.verification_expectations),
        "",
    ]

    (plans_dir / prd_name).write_text("\n".join(prd_lines), encoding="utf-8")
    (plans_dir / test_spec_name).write_text(
        "\n".join(test_spec_lines), encoding="utf-8"
    )
    (plans_dir / dag_name).write_text(f"{dag_text}\n", encoding="utf-8")
