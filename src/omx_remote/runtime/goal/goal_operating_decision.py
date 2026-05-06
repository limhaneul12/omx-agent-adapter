import orjson

from omx_remote.schemas.codex_goal.lifecycle_schemas import (
    CodexGoalLifecycleRestoredState,
)
from omx_remote.schemas.codex_goal.operating_schemas import (
    CodexGoalEvidenceRequirement,
    CodexGoalOperatingDecisionRequest,
    CodexGoalOperatingDecisionResult,
)
from omx_remote.shared.omx_enums.codex_goal_enums import (
    CodexGoalLifecycleRestoreTarget,
    CodexGoalOperatingAction,
    CodexGoalOperatingEvidenceSource,
    CodexGoalOperatingStage,
)


def _omx_team_api_command(operation: str, payload: dict[str, str]) -> str:
    """Builds a stable human-readable OMX Team API command hint.

    Args:
        operation [str]: OMX Team API operation name.
        payload [dict[str, str]]: JSON input payload for the operation.

    Returns:
        str: Command hint suitable for agent-facing JSON output.
    """
    input_payload: str = orjson.dumps(payload).decode()
    command: str = f"omx team api {operation} --input '{input_payload}' --json"
    return command


def _worker_status_commands(request: CodexGoalOperatingDecisionRequest) -> tuple[str, ...]:
    """Builds worker-status command hints from the restored Goal mirror state.

    Args:
        request [CodexGoalOperatingDecisionRequest]: Operating decision request.

    Returns:
        tuple[str, ...]: One command per expected worker.
    """
    worker_count: int = request.restored_state.bundle.mirror_state.team_worker_count or 0
    commands: tuple[str, ...] = tuple(
        _omx_team_api_command(
            "read-worker-status",
            {"team_name": request.team_name, "worker": f"worker-{worker_number}"},
        )
        for worker_number in range(1, worker_count + 1)
    )
    return commands


def _team_admin_commands(request: CodexGoalOperatingDecisionRequest) -> tuple[str, ...]:
    """Builds read-only Team Admin aggregation evidence commands.

    Args:
        request [CodexGoalOperatingDecisionRequest]: Operating decision request.

    Returns:
        tuple[str, ...]: Read-only OMX command hints for Team evidence collection.
    """
    list_tasks_command: str = _omx_team_api_command(
        "list-tasks",
        {"team_name": request.team_name},
    )
    read_events_command: str = _omx_team_api_command(
        "read-events",
        {"team_name": request.team_name},
    )
    commands: tuple[str, ...] = (
        list_tasks_command,
        read_events_command,
        *_worker_status_commands(request),
    )
    return commands


def _evidence_requirement(
    source: CodexGoalOperatingEvidenceSource,
    required: bool,
    available: bool,
    summary: str,
    command: str | None = None,
) -> CodexGoalEvidenceRequirement:
    """Builds one evidence requirement contract.

    Args:
        source [CodexGoalOperatingEvidenceSource]: Evidence source name.
        required [bool]: Whether the source is required for the selected action.
        available [bool]: Whether the source is already available in restored artifacts.
        summary [str]: Agent-facing evidence summary.
        command [str | None]: Optional command hint for collecting the evidence.

    Returns:
        CodexGoalEvidenceRequirement: Evidence requirement contract.
    """
    requirement = CodexGoalEvidenceRequirement.model_validate(
        {
            "source": source,
            "required": required,
            "available": available,
            "command": command,
            "summary": summary,
        }
    )
    return requirement


def _artifact_evidence(restored_state: CodexGoalLifecycleRestoredState) -> tuple[CodexGoalEvidenceRequirement, ...]:
    """Builds available artifact evidence from restored lifecycle state.

    Args:
        restored_state [CodexGoalLifecycleRestoredState]: Restored lifecycle state.

    Returns:
        tuple[CodexGoalEvidenceRequirement, ...]: Available artifact evidence requirements.
    """
    bundle = restored_state.bundle
    evidence: tuple[CodexGoalEvidenceRequirement, ...] = (
        _evidence_requirement(
            CodexGoalOperatingEvidenceSource.GOAL_LIFECYCLE_ARTIFACT,
            required=True,
            available=True,
            summary="Durable Goal lifecycle artifact bundle was restored.",
        ),
    )
    if bundle.aggregation_report is not None:
        evidence = (
            *evidence,
            _evidence_requirement(
                CodexGoalOperatingEvidenceSource.TEAM_ADMIN_AGGREGATION_REPORT,
                required=True,
                available=True,
                summary="Team Admin aggregation report is already present.",
            ),
        )
    if bundle.ralph_review_result is not None:
        evidence = (
            *evidence,
            _evidence_requirement(
                CodexGoalOperatingEvidenceSource.RALPH_POST_TEAM_REVIEW_RESULT,
                required=True,
                available=True,
                summary="Ralph post-Team review result is already present.",
            ),
        )
    if bundle.lifecycle_decision is not None:
        evidence = (
            *evidence,
            _evidence_requirement(
                CodexGoalOperatingEvidenceSource.GOAL_LIFECYCLE_DECISION,
                required=True,
                available=True,
                summary="Goal lifecycle decision is already present.",
            ),
        )

    result: tuple[CodexGoalEvidenceRequirement, ...] = evidence
    return result


def _team_admin_missing_evidence(
    request: CodexGoalOperatingDecisionRequest,
) -> tuple[CodexGoalEvidenceRequirement, ...]:
    """Builds missing read-only OMX evidence required for Team Admin aggregation.

    Args:
        request [CodexGoalOperatingDecisionRequest]: Operating decision request.

    Returns:
        tuple[CodexGoalEvidenceRequirement, ...]: Missing Team API evidence sources.
    """
    commands: tuple[str, ...] = _team_admin_commands(request)
    worker_status_command: str | None = commands[2] if len(commands) > 2 else None
    evidence: tuple[CodexGoalEvidenceRequirement, ...] = (
        _evidence_requirement(
            CodexGoalOperatingEvidenceSource.OMX_TEAM_API_LIST_TASKS,
            required=True,
            available=False,
            command=commands[0],
            summary="Read Team task state before deriving Team Admin aggregation.",
        ),
        _evidence_requirement(
            CodexGoalOperatingEvidenceSource.OMX_TEAM_API_READ_EVENTS,
            required=True,
            available=False,
            command=commands[1],
            summary="Read Team event history before deriving Team Admin aggregation.",
        ),
        _evidence_requirement(
            CodexGoalOperatingEvidenceSource.OMX_TEAM_API_READ_WORKER_STATUS,
            required=True,
            available=False,
            command=worker_status_command,
            summary="Read worker status snapshots before deriving Team Admin aggregation.",
        ),
    )
    return evidence


def _available_sources(evidence: tuple[CodexGoalEvidenceRequirement, ...]) -> tuple[str, ...]:
    """Collects available evidence source names.

    Args:
        evidence [tuple[CodexGoalEvidenceRequirement, ...]]: Evidence requirements.

    Returns:
        tuple[str, ...]: Available evidence source names.
    """
    sources: tuple[str, ...] = tuple(
        requirement.source for requirement in evidence if requirement.available
    )
    return sources


def _missing_sources(evidence: tuple[CodexGoalEvidenceRequirement, ...]) -> tuple[str, ...]:
    """Collects missing required evidence source names.

    Args:
        evidence [tuple[CodexGoalEvidenceRequirement, ...]]: Evidence requirements.

    Returns:
        tuple[str, ...]: Missing evidence source names.
    """
    sources: tuple[str, ...] = tuple(
        requirement.source
        for requirement in evidence
        if requirement.required and not requirement.available
    )
    return sources


def _commands(evidence: tuple[CodexGoalEvidenceRequirement, ...]) -> tuple[str, ...]:
    """Collects available command hints from evidence requirements.

    Args:
        evidence [tuple[CodexGoalEvidenceRequirement, ...]]: Evidence requirements.

    Returns:
        tuple[str, ...]: Recommended command hints.
    """
    commands: tuple[str, ...] = tuple(
        requirement.command for requirement in evidence if requirement.command is not None
    )
    return commands


def _stage_for_target(
    target: CodexGoalLifecycleRestoreTarget,
) -> CodexGoalOperatingStage:
    """Maps a lifecycle restore target to an agent operating stage.

    Args:
        target [CodexGoalLifecycleRestoreTarget]: Restored lifecycle resume target.

    Returns:
        CodexGoalOperatingStage: Agent-facing operating stage.
    """
    if target == CodexGoalLifecycleRestoreTarget.TEAM_ADMIN_AGGREGATION:
        stage = CodexGoalOperatingStage.TEAM_ADMIN_AGGREGATION_PENDING
    elif target == CodexGoalLifecycleRestoreTarget.RALPH_POST_TEAM_REVIEW:
        stage = CodexGoalOperatingStage.RALPH_POST_TEAM_REVIEW_PENDING
    elif target == CodexGoalLifecycleRestoreTarget.GOAL_LIFECYCLE_DECISION:
        stage = CodexGoalOperatingStage.GOAL_LIFECYCLE_DECISION_PENDING
    elif target == CodexGoalLifecycleRestoreTarget.GOAL_CLOSE:
        stage = CodexGoalOperatingStage.GOAL_CLOSE_READY
    elif target == CodexGoalLifecycleRestoreTarget.RALPH_FOLLOW_UP:
        stage = CodexGoalOperatingStage.RALPH_FOLLOW_UP_READY
    else:
        stage = CodexGoalOperatingStage.HUMAN_REVIEW_REQUIRED

    return stage


def _action_for_stage(stage: CodexGoalOperatingStage) -> CodexGoalOperatingAction:
    """Maps an operating stage to the next agent action.

    Args:
        stage [CodexGoalOperatingStage]: Agent-facing operating stage.

    Returns:
        CodexGoalOperatingAction: Next recommended action.
    """
    if stage == CodexGoalOperatingStage.TEAM_ADMIN_AGGREGATION_PENDING:
        action = CodexGoalOperatingAction.COLLECT_TEAM_ADMIN_AGGREGATION
    elif stage == CodexGoalOperatingStage.RALPH_POST_TEAM_REVIEW_PENDING:
        action = CodexGoalOperatingAction.RUN_RALPH_POST_TEAM_REVIEW
    elif stage == CodexGoalOperatingStage.GOAL_LIFECYCLE_DECISION_PENDING:
        action = CodexGoalOperatingAction.BUILD_GOAL_LIFECYCLE_DECISION
    elif stage == CodexGoalOperatingStage.GOAL_CLOSE_READY:
        action = CodexGoalOperatingAction.CLOSE_GOAL
    elif stage == CodexGoalOperatingStage.RALPH_FOLLOW_UP_READY:
        action = CodexGoalOperatingAction.PREPARE_RALPH_FOLLOW_UP
    else:
        action = CodexGoalOperatingAction.WAIT_FOR_HUMAN_REVIEW

    return action


def _safe_to_mutate(stage: CodexGoalOperatingStage) -> bool:
    """Decides whether the next action may mutate Goal/OMX state.

    Args:
        stage [CodexGoalOperatingStage]: Agent-facing operating stage.

    Returns:
        bool: True when the action can proceed without more evidence collection.
    """
    safe: bool = stage == CodexGoalOperatingStage.GOAL_CLOSE_READY
    return safe


def _requires_review(stage: CodexGoalOperatingStage) -> bool:
    """Decides whether the operating decision must stop for review.

    Args:
        stage [CodexGoalOperatingStage]: Agent-facing operating stage.

    Returns:
        bool: True when a human/reviewer gate is required.
    """
    requires_review: bool = stage == CodexGoalOperatingStage.HUMAN_REVIEW_REQUIRED
    return requires_review


def _review_blockers(restored_state: CodexGoalLifecycleRestoredState) -> tuple[str, ...]:
    """Reads review blockers from the lifecycle decision when present.

    Args:
        restored_state [CodexGoalLifecycleRestoredState]: Restored lifecycle state.

    Returns:
        tuple[str, ...]: Review blockers that prevent mutation.
    """
    lifecycle_decision = restored_state.bundle.lifecycle_decision
    if lifecycle_decision is None:
        blockers: tuple[str, ...] = ()
    else:
        blockers = lifecycle_decision.review_blockers

    return blockers


def _build_summary(
    request: CodexGoalOperatingDecisionRequest,
    stage: CodexGoalOperatingStage,
    action: CodexGoalOperatingAction,
) -> str:
    """Builds an agent-facing operating decision summary.

    Args:
        request [CodexGoalOperatingDecisionRequest]: Operating decision request.
        stage [CodexGoalOperatingStage]: Selected operating stage.
        action [CodexGoalOperatingAction]: Selected next action.

    Returns:
        str: Stable summary of the recommendation.
    """
    goal_id: str = request.restored_state.bundle.goal_id
    summary: str = f"Goal {goal_id} is at {stage}; recommended next action is {action}."
    return summary


def build_goal_operating_decision(
    request: CodexGoalOperatingDecisionRequest,
) -> CodexGoalOperatingDecisionResult:
    """Builds an agent-facing next action recommendation from Goal lifecycle artifacts.

    Args:
        request [CodexGoalOperatingDecisionRequest]: Restored lifecycle state and Team name.

    Returns:
        CodexGoalOperatingDecisionResult: Evidence map and recommended next action.
    """
    target = CodexGoalLifecycleRestoreTarget(request.restored_state.next_resume_target)
    stage: CodexGoalOperatingStage = _stage_for_target(target)
    action: CodexGoalOperatingAction = _action_for_stage(stage)
    evidence: tuple[CodexGoalEvidenceRequirement, ...] = _artifact_evidence(
        request.restored_state
    )
    if stage == CodexGoalOperatingStage.TEAM_ADMIN_AGGREGATION_PENDING:
        evidence = (*evidence, *_team_admin_missing_evidence(request))

    recommended_commands: tuple[str, ...]
    if stage == CodexGoalOperatingStage.TEAM_ADMIN_AGGREGATION_PENDING:
        recommended_commands = _team_admin_commands(request)
    else:
        recommended_commands = _commands(evidence)

    decision = CodexGoalOperatingDecisionResult.model_validate(
        {
            "goal_id": request.restored_state.bundle.goal_id,
            "current_stage": stage,
            "next_action": action,
            "safe_to_mutate": _safe_to_mutate(stage),
            "requires_review": _requires_review(stage),
            "available_evidence": _available_sources(evidence),
            "missing_evidence": _missing_sources(evidence),
            "evidence_requirements": evidence,
            "recommended_commands": recommended_commands,
            "review_blockers": _review_blockers(request.restored_state),
            "summary": _build_summary(request, stage, action),
        }
    )
    return decision
