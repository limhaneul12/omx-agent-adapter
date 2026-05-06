from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from shutil import which
from typing import ClassVar

import orjson
from pydantic import ValidationError

from omx_remote.schemas.invoke_schemas import OmxCommandResult
from omx_remote.schemas.ralph import RalphPrdArtifact, TeamWorkerAssignment
from omx_remote.shared.omx_enums.ralph_enums import (
    RalphRunOutcome,
    RalphRuntimePhase,
    RalphStateClassification,
)
from omx_remote.shared.utils.json_file_store import json_file_stores

_RALPH_STATE_FILENAMES: tuple[str, ...] = (
    "ralph-state.json",
    "ralph-progress.json",
    "run-state.json",
)


def _normalize_token(value: object) -> str | None:
    token: str
    if not isinstance(value, str):
        return None

    token = value.strip().lower()
    return token or None


def _read_json_object(path: Path) -> dict[str, object] | None:
    state_store = json_file_stores.for_path(path)
    object_payload: dict[str, object] | None = state_store.read_object()
    return object_payload


def _summarize_prd_validation_error(validation_error: ValidationError) -> str:
    field_paths: list[str] = []

    for error_payload in validation_error.errors():
        raw_location: object = error_payload.get("loc")
        if not isinstance(raw_location, tuple):
            continue

        location_parts: list[str] = [str(location_token) for location_token in raw_location]
        if not location_parts:
            continue

        field_paths.append(".".join(location_parts))

    if not field_paths:
        invalid_field_summary: str = "typed Ralph PRD fields"
        return invalid_field_summary

    invalid_field_summary = ", ".join(field_paths)
    return invalid_field_summary


def read_ralph_prd_artifact(prd_path: Path) -> RalphPrdArtifact:
    prd_payload: dict[str, object] | None = _read_json_object(prd_path)
    if prd_payload is None:
        raise ValueError("Invalid or unreadable .omx/prd.json: expected JSON object.")

    try:
        artifact: RalphPrdArtifact = RalphPrdArtifact.model_validate(prd_payload)
    except ValidationError as validation_error:
        invalid_fields: str = _summarize_prd_validation_error(validation_error)
        raise ValueError(
            "Invalid .omx/prd.json: expected a typed Ralph PRD artifact with fields "
            f"{invalid_fields}."
        ) from validation_error

    return artifact



def _normalize_objective_text(objective_text: str) -> str:
    normalized_objective_text: str = objective_text.strip().lower()
    return normalized_objective_text



def _resolve_ralph_launch_task_from_prd(
    *,
    task: str,
    ralph_prd_artifact: RalphPrdArtifact,
) -> str:
    normalized_task_text: str = _normalize_objective_text(task)
    normalized_prd_objective_text: str = _normalize_objective_text(
        ralph_prd_artifact.objective
    )
    if normalized_task_text != normalized_prd_objective_text:
        raise ValueError(
            "Launch task text must match the typed Ralph PRD objective in .omx/prd.json before execution proceeds."
        )

    canonical_launch_task: str = ralph_prd_artifact.objective.strip()
    return canonical_launch_task



def _resolve_ralph_team_launch_task_from_prd(
    *,
    ralph_prd_artifact: RalphPrdArtifact,
) -> tuple[str, int]:
    if not ralph_prd_artifact.requires_team_fanout:
        raise ValueError(
            "The typed Ralph PRD artifact does not request Team fanout, so Team launch cannot proceed."
        )

    team_worker_count: int | None = ralph_prd_artifact.team_worker_count
    if team_worker_count is None:
        raise ValueError(
            "The typed Ralph PRD artifact requires Team fanout but does not declare team_worker_count."
        )

    if ralph_prd_artifact.team_worker_assignments is None:
        raise ValueError(
            "The typed Ralph PRD artifact requires Team fanout but does not declare Team worker assignments."
        )

    canonical_launch_task: str = ralph_prd_artifact.objective.strip()
    return canonical_launch_task, team_worker_count



class RalphStateClassifier:
    """Classifies adapter-visible Ralph runtime state markers."""

    TERMINAL_PHASES: ClassVar[frozenset[RalphRuntimePhase]] = frozenset(
        {
            RalphRuntimePhase.COMPLETE,
            RalphRuntimePhase.COMPLETED,
            RalphRuntimePhase.FAILED,
            RalphRuntimePhase.CANCELLED,
        }
    )
    NON_TERMINAL_PHASES: ClassVar[frozenset[RalphRuntimePhase]] = frozenset(
        {
            RalphRuntimePhase.STARTING,
            RalphRuntimePhase.RUNNING,
            RalphRuntimePhase.EXECUTING,
            RalphRuntimePhase.PLANNING,
            RalphRuntimePhase.ACTIVE,
            RalphRuntimePhase.PAUSED,
            RalphRuntimePhase.IDLE,
            RalphRuntimePhase.USER_INTERLUDE,
            RalphRuntimePhase.BLOCKED_ON_USER,
            RalphRuntimePhase.WAITING,
        }
    )
    TERMINAL_OUTCOMES: ClassVar[frozenset[RalphRunOutcome]] = frozenset(
        {
            RalphRunOutcome.FINISH,
            RalphRunOutcome.BLOCKED_ON_USER,
            RalphRunOutcome.FAILED,
            RalphRunOutcome.CANCELLED,
            RalphRunOutcome.COMPLETE,
            RalphRunOutcome.COMPLETED,
            RalphRunOutcome.DONE,
            RalphRunOutcome.USER_INTERLUDE,
        }
    )
    NON_TERMINAL_OUTCOMES: ClassVar[frozenset[RalphRunOutcome]] = frozenset(
        {
            RalphRunOutcome.CONTINUE,
            RalphRunOutcome.PROGRESS,
            RalphRunOutcome.RUNNING,
            RalphRunOutcome.ACTIVE,
        }
    )

    @staticmethod
    def normalize_phase(phase_value: object) -> RalphRuntimePhase | None:
        normalized_phase: str | None = _normalize_token(phase_value)
        if normalized_phase is None:
            missing_phase: RalphRuntimePhase | None = None
            return missing_phase

        try:
            parsed_phase: RalphRuntimePhase = RalphRuntimePhase(normalized_phase)
        except ValueError:
            unknown_phase: RalphRuntimePhase | None = None
            return unknown_phase

        return parsed_phase

    @staticmethod
    def normalize_outcome(outcome_value: object) -> RalphRunOutcome | None:
        normalized_outcome: str | None = _normalize_token(outcome_value)
        if normalized_outcome is None:
            missing_outcome: RalphRunOutcome | None = None
            return missing_outcome

        try:
            parsed_outcome: RalphRunOutcome = RalphRunOutcome(normalized_outcome)
        except ValueError:
            unknown_outcome: RalphRunOutcome | None = None
            return unknown_outcome

        return parsed_outcome

    @classmethod
    def is_terminal_phase(cls, phase_value: object) -> bool:
        phase: RalphRuntimePhase | None = cls.normalize_phase(phase_value)
        terminal_phase: bool = phase in cls.TERMINAL_PHASES
        return terminal_phase

    @classmethod
    def is_terminal_outcome(cls, outcome_value: object) -> bool:
        outcome: RalphRunOutcome | None = cls.normalize_outcome(outcome_value)
        terminal_outcome: bool = outcome in cls.TERMINAL_OUTCOMES
        return terminal_outcome

    @classmethod
    def is_active_phase(cls, phase_value: object) -> bool:
        phase: RalphRuntimePhase | None = cls.normalize_phase(phase_value)
        active_phase: bool = phase in cls.NON_TERMINAL_PHASES
        return active_phase

    @classmethod
    def is_active_outcome(cls, outcome_value: object) -> bool:
        outcome: RalphRunOutcome | None = cls.normalize_outcome(outcome_value)
        active_outcome: bool = outcome in cls.NON_TERMINAL_OUTCOMES
        return active_outcome

    @classmethod
    def classify_state_snapshot(
        cls,
        state_payload: dict[str, object],
    ) -> RalphStateClassification:
        """Classifies a Ralph state artifact as resumable, terminal, or stale."""
        active_value: object | None = state_payload.get("active")

        if active_value is True:
            resumable_state: RalphStateClassification = RalphStateClassification.RESUMABLE
            return resumable_state

        if active_value is False:
            false_active_state: RalphStateClassification = cls._classify_inactive_state(
                state_payload
            )
            return false_active_state

        if active_value is not None and not isinstance(active_value, bool):
            stale_state: RalphStateClassification = RalphStateClassification.STALE
            return stale_state

        unknown_active_state: RalphStateClassification = cls._classify_marker_state(
            state_payload
        )
        return unknown_active_state

    @classmethod
    def _classify_inactive_state(
        cls,
        state_payload: dict[str, object],
    ) -> RalphStateClassification:
        outcome_value: object | None = cls._read_outcome_value(state_payload)
        if cls.is_terminal_outcome(outcome_value):
            terminal_state: RalphStateClassification = RalphStateClassification.TERMINAL
            return terminal_state

        phase_value: object | None = state_payload.get("current_phase")
        if cls.is_terminal_phase(phase_value):
            terminal_state = RalphStateClassification.TERMINAL
            return terminal_state

        if cls.is_active_outcome(outcome_value) or cls.is_active_phase(phase_value):
            resumable_state: RalphStateClassification = RalphStateClassification.RESUMABLE
            return resumable_state

        stale_state: RalphStateClassification = RalphStateClassification.STALE
        return stale_state

    @classmethod
    def _classify_marker_state(
        cls,
        state_payload: dict[str, object],
    ) -> RalphStateClassification:
        outcome_value: object | None = cls._read_outcome_value(state_payload)
        phase_value: object | None = state_payload.get("current_phase")

        if cls.is_terminal_outcome(outcome_value):
            terminal_state: RalphStateClassification = RalphStateClassification.TERMINAL
            return terminal_state

        if cls.is_active_outcome(outcome_value) or cls.is_active_phase(phase_value):
            resumable_state: RalphStateClassification = RalphStateClassification.RESUMABLE
            return resumable_state

        if cls.is_terminal_phase(phase_value):
            terminal_state = RalphStateClassification.TERMINAL
            return terminal_state

        stale_state: RalphStateClassification = RalphStateClassification.STALE
        return stale_state

    @staticmethod
    def _read_outcome_value(state_payload: dict[str, object]) -> object | None:
        outcome_value: object | None = state_payload.get("run_outcome")
        if outcome_value is None:
            outcome_value = state_payload.get("outcome")

        return outcome_value


def _classify_ralph_state_snapshot(
    state_payload: dict[str, object],
) -> RalphStateClassification:
    """Classify Ralph state as resumable / terminal / stale."""
    state_classification: RalphStateClassification = (
        RalphStateClassifier.classify_state_snapshot(state_payload)
    )
    return state_classification


def _assess_ralph_launch_preflight_state() -> tuple[RalphStateClassification, list[str]]:
    existing_state_paths: list[Path] = list_ralph_state_paths()
    if not existing_state_paths:
        return RalphStateClassification.CLEAN, []

    ralph_state_path: Path = get_ralph_state_root() / "ralph-state.json"
    if ralph_state_path not in existing_state_paths:
        joined_paths: str = ", ".join(str(path) for path in existing_state_paths)
        return RalphStateClassification.STALE, [
            "Existing Ralph state files were found, but no ralph-state.json was present.",
            f"Known stale files: {joined_paths}",
            "If these are stale, run `agent-remote ralph cleanup-stale` before re-launching.",
        ]

    ralph_state_payload: dict[str, object] | None = _read_json_object(ralph_state_path)
    if ralph_state_payload is None:
        joined_paths: str = ", ".join(str(path) for path in existing_state_paths)
        return RalphStateClassification.TERMINAL, [
            "Ralph state artifact is present but unreadable.",
            f"Paths: {joined_paths}",
            "Clean stale Ralph artifacts and retry with `agent-remote ralph cleanup-stale`.",
        ]

    state_class: RalphStateClassification = _classify_ralph_state_snapshot(ralph_state_payload)
    joined_paths = ", ".join(str(path) for path in existing_state_paths)

    if state_class == RalphStateClassification.RESUMABLE:
        return RalphStateClassification.RESUMABLE, [
            "Ralph appears resumable from existing state.",
            f"Paths: {joined_paths}",
            "If you intend to start a new session, run `agent-remote ralph cleanup-stale` or use --force-cleanup.",
        ]

    if state_class == RalphStateClassification.TERMINAL:
        return RalphStateClassification.TERMINAL, [
            "Ralph state exists and is terminal/non-runnable.",
            f"Paths: {joined_paths}",
            "Proceeding is treated as a stale-state recovery path.",
        ]

    return RalphStateClassification.STALE, [
        "Ralph state exists but lacks explicit resumability markers.",
        f"Paths: {joined_paths}",
        "Proceeding may overwrite stale artifacts unless you run cleanup first.",
    ]


def _assess_ralph_resume_preflight_state() -> tuple[RalphStateClassification, list[str]]:
    existing_state_paths: list[Path] = list_ralph_state_paths()
    if not existing_state_paths:
        return RalphStateClassification.MISSING, ["No Ralph state files found."]

    ralph_state_path = get_ralph_state_root() / "ralph-state.json"
    if not ralph_state_path.exists():
        joined_paths: str = ", ".join(str(path) for path in existing_state_paths)
        return RalphStateClassification.INVALID, [
            "Ralph state exists without a canonical ralph-state.json.",
            f"Known Ralph files: {joined_paths}",
            "Run cleanup-stale and re-run launch if this is stale recovery.",
        ]

    state_payload: dict[str, object] | None = _read_json_object(ralph_state_path)
    if state_payload is None:
        return RalphStateClassification.INVALID, [
            "Ralph state file is present but unreadable.",
            f"Path: {ralph_state_path}",
        ]

    state_class: RalphStateClassification = _classify_ralph_state_snapshot(state_payload)
    if state_class != RalphStateClassification.RESUMABLE:
        return state_class, [
            f"Ralph state file class is '{state_class}'.",
            "Resume requires an active or non-terminal Ralph state.",
        ]

    warnings: list[str] = ["Ralph state classified as resumable."]
    ralph_progress_path = get_ralph_state_root() / "ralph-progress.json"
    if not ralph_progress_path.exists():
        warnings.append("Ralph progress artifact is missing; resume may lose progress history.")

    return RalphStateClassification.RESUMABLE, warnings


def _validate_ralph_prd_gate() -> RalphPrdArtifact:
    prd_path: Path = Path.cwd() / ".omx" / "prd.json"
    if not prd_path.exists():
        raise ValueError(
            "Missing required PRD.json at .omx/prd.json. Create the file before running `agent-remote ralph launch`."
        )

    artifact: RalphPrdArtifact = read_ralph_prd_artifact(prd_path)
    return artifact


def _detect_tty_tmux_gate(*, allow_non_tty: bool) -> list[str]:
    warnings: list[str] = []
    if which("tmux") is None:
        warnings.append(
            "tmux was not detected. Ralph runs in direct mode without detached tmux HUD. "
            "Install tmux for the normal launch UX."
        )

    if allow_non_tty:
        warnings.append(
            "allow-non-tty is enabled; launch behavior may differ from interactive-tty mode."
        )

    return warnings



def _detect_team_tty_tmux_gate(*, allow_non_tty: bool) -> list[str]:
    warnings: list[str] = []
    if which("tmux") is None:
        warnings.append(
            "tmux was not detected. Team runs in direct mode without detached tmux HUD. "
            "Install tmux for the normal launch UX."
        )

    if allow_non_tty:
        warnings.append(
            "allow-non-tty is enabled; launch behavior may differ from interactive-tty mode."
        )

    return warnings



def get_ralph_state_root(workspace_root: Path | None = None) -> Path:
    """Return the OMX state directory for the current workspace.

    Args:
        workspace_root [Path | None]: Optional explicit workspace root.

    Returns:
        Path: The `.omx/state` directory path for the workspace.
    """
    resolved_workspace_root: Path
    if workspace_root is None:
        resolved_workspace_root = Path.cwd()
    else:
        resolved_workspace_root = workspace_root

    state_root: Path = resolved_workspace_root / ".omx" / "state"
    return state_root


def list_ralph_state_paths(workspace_root: Path | None = None) -> list[Path]:
    """List known Ralph state paths that currently exist.

    Args:
        workspace_root [Path | None]: Optional explicit workspace root.

    Returns:
        list[Path]: Existing known Ralph state files.
    """
    state_root: Path = get_ralph_state_root(workspace_root=workspace_root)
    existing_state_paths: list[Path] = []

    relative_name: str
    for relative_name in _RALPH_STATE_FILENAMES:
        state_path: Path = state_root / relative_name
        if state_path.exists():
            existing_state_paths.append(state_path)

    return existing_state_paths


def require_ralph_launch_tty(*, allow_non_tty: bool) -> None:
    """Validate whether Ralph launch may proceed in the current stdin mode.

    Args:
        allow_non_tty [bool]: Whether non-interactive launch is explicitly allowed.

    Raises:
        ValueError: If stdin is not a TTY and non-interactive launch was not allowed.
    """
    if allow_non_tty:
        return

    if not sys.stdin.isatty():
        raise ValueError(
            "Ralph launch requires an interactive TTY. Retry from a terminal or pass --allow-non-tty."
        )


def validate_ralph_launch_task(task: str) -> str:
    """Normalize and validate task text for Ralph launch.

    Args:
        task [str]: Raw task text from the CLI.

    Returns:
        str: Stripped non-blank task text.

    Raises:
        ValueError: If the task text is blank after stripping.
    """
    normalized_task: str = task.strip()
    if normalized_task == "":
        raise ValueError("Task text must not be blank.")

    return normalized_task


def launch_ralph_command(
    task: str,
    *,
    force_cleanup: bool,
    allow_non_tty: bool,
) -> list[str]:
    """Build the Ralph launch command after preflight validation.

    Args:
        task [str]: Raw task text from the CLI.
        force_cleanup [bool]: Whether to proceed when stale state exists.
        allow_non_tty [bool]: Whether non-interactive launch is explicitly allowed.

    Returns:
        list[str]: OMX argv for the Ralph launch command.

    Raises:
        ValueError: If the task is blank or stale state exists without force.
    """
    launch_command, _warnings = build_ralph_launch_plan(
        task,
        force_cleanup=force_cleanup,
        allow_non_tty=allow_non_tty,
    )
    return launch_command


def build_ralph_launch_plan(
    task: str,
    *,
    force_cleanup: bool,
    allow_non_tty: bool,
) -> tuple[list[str], list[str]]:
    """Build launch command and preflight warnings.

    Args:
        task [str]: Raw task text from CLI.
        force_cleanup [bool]: Whether to proceed when stale/running state exists.
        allow_non_tty [bool]: Whether non-interactive launch is explicitly allowed.

    Returns:
        tuple[list[str], list[str]]: Command plus preflight warnings.

    Raises:
        ValueError: If task is blank, TTY/timer checks fail, PRD gate blocks, or stale active state blocks.
    """
    normalized_task: str = validate_ralph_launch_task(task)
    require_ralph_launch_tty(allow_non_tty=allow_non_tty)

    warnings: list[str] = []
    warnings.extend(_detect_tty_tmux_gate(allow_non_tty=allow_non_tty))
    ralph_prd_artifact: RalphPrdArtifact = _validate_ralph_prd_gate()
    canonical_launch_task: str = _resolve_ralph_launch_task_from_prd(
        task=normalized_task,
        ralph_prd_artifact=ralph_prd_artifact,
    )

    state_class, state_warnings = _assess_ralph_launch_preflight_state()
    warnings.extend(state_warnings)

    if state_class == RalphStateClassification.RESUMABLE and not force_cleanup:
        raise ValueError(
            "Existing resumable Ralph state detected. Run `agent-remote ralph cleanup-stale` "
            "or retry with --force-cleanup."
        )

    launch_command: list[str] = ["ralph", "--prd", canonical_launch_task]
    return launch_command, warnings



def _quote_omx_task(task: str) -> str:
    quoted_task: str = orjson.dumps(task).decode()
    return quoted_task


def _format_markdown_list(values: tuple[str, ...] | list[str]) -> str:
    if not values:
        return "- none"
    return "\n".join(f"- {value}" for value in values)


def _render_worker_assignment_description(assignment: TeamWorkerAssignment) -> str:
    description: str = f"""Lane: {assignment.lane_name}
Objective: {assignment.objective}

Owned files:
{_format_markdown_list(assignment.owned_files)}

Read-only context files:
{_format_markdown_list(assignment.read_only_context_files)}

Forbidden files / coordination notes:
{_format_markdown_list(assignment.forbidden_files)}

TDD steps:
{_format_markdown_list(assignment.tdd_steps)}

Verification commands:
{_format_markdown_list(assignment.verification_commands)}

Handoff summary required:
- {assignment.handoff_summary_required}

Authorization policy: {assignment.authorization_policy}

Allowed commands:
{_format_markdown_list(assignment.authorization_scope.allowed_commands)}

Forbidden commands:
{_format_markdown_list(assignment.authorization_scope.forbidden_commands)}

Requires human approval for:
{_format_markdown_list(assignment.authorization_scope.requires_human_for)}

Requires LLM review for:
{_format_markdown_list(assignment.authorization_scope.requires_llm_review_for)}
""".strip()
    return description


def _build_worker_authorization_payload(
    assignment: TeamWorkerAssignment,
) -> dict[str, object]:
    authorization_payload: dict[str, object] = {
        "policy": assignment.authorization_policy,
        "allowed_commands": list(assignment.authorization_scope.allowed_commands),
        "forbidden_commands": list(assignment.authorization_scope.forbidden_commands),
        "requires_human_for": list(assignment.authorization_scope.requires_human_for),
        "requires_llm_review_for": list(
            assignment.authorization_scope.requires_llm_review_for
        ),
    }
    return authorization_payload


def _planning_artifact_slug() -> str:
    timestamp: str = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    slug: str = f"{timestamp}-ralph-team"
    return slug


def _write_ralph_team_dag_handoff_artifacts(
    *,
    ralph_prd_artifact: RalphPrdArtifact,
    canonical_launch_task: str,
    team_worker_count: int,
    workspace_root: Path,
) -> None:
    assignments: tuple[TeamWorkerAssignment, ...] | None = (
        ralph_prd_artifact.team_worker_assignments
    )
    if assignments is None:
        raise ValueError(
            "The typed Ralph PRD artifact requires Team fanout but does not declare Team worker assignments."
        )

    plans_dir: Path = workspace_root / ".omx" / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)

    artifact_slug: str = _planning_artifact_slug()
    prd_name: str = f"prd-{artifact_slug}.md"
    test_spec_name: str = f"test-spec-{artifact_slug}.md"
    dag_name: str = f"team-dag-{artifact_slug}.json"
    launch_hint: str = (
        f"omx team {team_worker_count}:executor {_quote_omx_task(canonical_launch_task)}"
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
        _format_markdown_list(ralph_prd_artifact.scope),
        "",
        "## Constraints",
        _format_markdown_list(ralph_prd_artifact.constraints),
        "",
        "## Execution Plan",
        _format_markdown_list(ralph_prd_artifact.execution_plan),
        "",
        "## Verification Expectations",
        _format_markdown_list(ralph_prd_artifact.verification_expectations),
        "",
        "## Team DAG Handoff",
        "```json",
    ]
    dag_payload: dict[str, object] = {
        "schema_version": 1,
        "plan_slug": artifact_slug,
        "source_prd": prd_name,
        "worker_policy": {
            "requested_count": team_worker_count,
            "count_source": "plan-suggested",
            "strict_max_count": True,
        },
        "nodes": [
            {
                "id": assignment.worker_id,
                "subject": assignment.lane_name,
                "description": _render_worker_assignment_description(assignment),
                "role": "executor",
                "lane": assignment.lane_name,
                "filePaths": list(assignment.owned_files),
                "depends_on": [],
                "authorization": _build_worker_authorization_payload(assignment),
                "acceptance": [
                    *assignment.verification_commands,
                    assignment.handoff_summary_required,
                ],
            }
            for assignment in assignments
        ],
    }
    dag_text: str = orjson.dumps(dag_payload, option=orjson.OPT_INDENT_2).decode()
    prd_lines.extend([dag_text, "```", ""])

    test_spec_lines: list[str] = [
        "# Ralph Team Test Spec",
        "",
        "The approved Ralph Team PRD requires every worker lane to follow RED -> GREEN -> verification.",
        "",
        "## Required verification",
        _format_markdown_list(ralph_prd_artifact.verification_expectations),
        "",
    ]

    (plans_dir / prd_name).write_text("\n".join(prd_lines), encoding="utf-8")
    (plans_dir / test_spec_name).write_text(
        "\n".join(test_spec_lines), encoding="utf-8"
    )
    (plans_dir / dag_name).write_text(f"{dag_text}\n", encoding="utf-8")



def build_ralph_team_launch_plan(
    *,
    allow_non_tty: bool,
) -> tuple[list[str], list[str]]:
    """Build Team launch command from the typed Ralph PRD artifact."""
    require_ralph_launch_tty(allow_non_tty=allow_non_tty)

    warnings: list[str] = []
    warnings.extend(_detect_team_tty_tmux_gate(allow_non_tty=allow_non_tty))
    ralph_prd_artifact: RalphPrdArtifact = _validate_ralph_prd_gate()
    canonical_launch_task: str
    team_worker_count: int
    canonical_launch_task, team_worker_count = _resolve_ralph_team_launch_task_from_prd(
        ralph_prd_artifact=ralph_prd_artifact,
    )
    _write_ralph_team_dag_handoff_artifacts(
        ralph_prd_artifact=ralph_prd_artifact,
        canonical_launch_task=canonical_launch_task,
        team_worker_count=team_worker_count,
        workspace_root=Path.cwd(),
    )

    launch_command: list[str] = [
        "team",
        f"{team_worker_count}:executor",
        canonical_launch_task,
    ]
    return launch_command, warnings



def resume_ralph_command() -> list[str]:
    """Build the Ralph resume command after state preflight validation.

    Returns:
        list[str]: OMX argv for the Ralph resume command.

    Raises:
        ValueError: If no Ralph state exists to resume from.
    """
    state_class, _warnings = _assess_ralph_resume_preflight_state()
    if state_class != RalphStateClassification.RESUMABLE:
        if state_class == RalphStateClassification.MISSING:
            raise ValueError(
                "No Ralph state found. Launch Ralph first or restore a resumable Ralph state."
            )
        raise ValueError("No resumable Ralph session found for ralph.")

    resume_command: list[str] = ["ralph"]
    return resume_command


def build_ralph_resume_plan() -> tuple[list[str], list[str]]:
    """Build resume command and preflight warnings.

    Returns:
        tuple[list[str], list[str]]: Command plus resumability warnings.

    Raises:
        ValueError: If resume preflight fails.
    """
    state_class, warnings = _assess_ralph_resume_preflight_state()
    if state_class != RalphStateClassification.RESUMABLE:
        if state_class == RalphStateClassification.MISSING:
            raise ValueError(
                "No Ralph state found. Launch Ralph first or restore a resumable Ralph state."
            )
        raise ValueError("No resumable Ralph session found for ralph.")

    resume_command: list[str] = ["ralph"]
    return resume_command, warnings


def cleanup_ralph_state(workspace_root: Path | None = None) -> list[str]:
    """Remove known Ralph stale-state files.

    Args:
        workspace_root [Path | None]: Optional explicit workspace root.

    Returns:
        list[str]: Removed file paths as strings.
    """
    existing_state_paths: list[Path] = list_ralph_state_paths(workspace_root=workspace_root)
    removed_paths: list[str] = []

    state_path: Path
    for state_path in existing_state_paths:
        state_path.unlink()
        removed_paths.append(str(state_path))

    return removed_paths


def format_resume_outcome(command_result: OmxCommandResult) -> OmxCommandResult:
    """Normalize known Ralph resume non-resumable responses into a failure envelope.

    Args:
        command_result [OmxCommandResult]: Raw OMX command result.

    Returns:
        OmxCommandResult: Original result or a normalized preflight-style failure.
    """
    normalized_stdout: str = command_result.stdout.strip().lower()
    if (
        command_result.exit_code == 0
        and normalized_stdout == "no resumable team found for ralph"
    ):
        failure_result = format_preflight_failure(
            "No resumable Ralph session found. Launch Ralph first or restore a resumable Ralph runtime."
        )
        return failure_result

    return command_result


def format_preflight_failure(message: str) -> OmxCommandResult:
    """Return a typed command result for Ralph preflight failures.

    Args:
        message [str]: Preflight failure detail.

    Returns:
        OmxCommandResult: Normalized failure envelope.
    """
    failure_result = OmxCommandResult(exit_code=2, stdout="", stderr=message)
    return failure_result
